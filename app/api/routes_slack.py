import json
from urllib.parse import parse_qs
from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.config import settings
from app.db import db_session
from app.integrations.slack_client import verify_slack_signature
from app.integrations.slack_web_client import SlackWebClient
from app.repositories import (
    acquire_slack_processing_lock,
    add_search_topic,
    list_active_search_topics,
    record_slack_decision,
    release_slack_processing_lock_for_user,
    remove_search_topic,
    update_slack_processing_message,
)
from app.services.guardrails import extract_news_topic, validate_professional_ai_topic
from app.services.pipeline_service import run_news_pipeline_now
from app.services.search_query_planner import clean_search_topic

router = APIRouter()


@router.post("/actions")
async def slack_actions(request: Request) -> dict[str, str]:
    if not settings.slack_signing_secret:
        raise HTTPException(status_code=500, detail="Slack signing secret is not configured")
    body = await verify_slack_signature(request, settings.slack_signing_secret)
    payload = request.query_params.get("payload")
    if payload is None:
        payload = parse_qs(body.decode("utf-8")).get("payload", [None])[0] if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else None
    action_status = "received"
    if payload:
        data = json.loads(payload)
        actions = data.get("actions", [])
        if actions:
            action_id = actions[0].get("action_id")
            action_status = {
                "approve_article": "approved",
                "needs_edit_article": "needs_edit",
                "reject_article": "rejected",
            }.get(action_id, "received")
            run_id, article_id = _parse_action_value(actions[0].get("value"))
            user = data.get("user", {})
            channel = data.get("channel", {})
            message = data.get("message", {})
            if run_id:
                with db_session() as session:
                    record_slack_decision(
                        session=session,
                        run_id=run_id,
                        article_id=article_id,
                        action=action_status,
                        slack_user_id=user.get("id"),
                        slack_user_name=user.get("username") or user.get("name"),
                        slack_channel_id=channel.get("id"),
                        slack_message_ts=message.get("ts"),
                        raw_payload=data,
                    )
    _ = body
    return {"status": action_status}


def _parse_action_value(value: str | None) -> tuple[str | None, int | None]:
    if not value:
        return None, None
    run_id, _, article_id_value = value.partition(":")
    article_id = int(article_id_value) if article_id_value.isdigit() else None
    return run_id or None, article_id


@router.post("/commands")
async def slack_commands(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    if not settings.slack_signing_secret:
        raise HTTPException(status_code=500, detail="Slack signing secret is not configured")
    body = await verify_slack_signature(request, settings.slack_signing_secret)
    form = {key: values[0] for key, values in parse_qs(body.decode("utf-8")).items()}
    text = str(form.get("text", "")).strip()
    user_id = str(form.get("user_id") or "")
    user_name = str(form.get("user_name") or "")
    channel_id = str(form.get("channel_id") or "")
    response_text = _handle_topic_command(text, user_id=user_id, user_name=user_name, channel_id=channel_id, background_tasks=background_tasks)
    return {"response_type": "ephemeral", "text": response_text}


@router.post("/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    if not settings.slack_signing_secret:
        raise HTTPException(status_code=500, detail="Slack signing secret is not configured")
    body = await request.body()
    payload = json.loads(body)
    if payload.get("type") == "url_verification":
        return PlainTextResponse(str(payload.get("challenge", "")))

    await verify_slack_signature(request, settings.slack_signing_secret)

    event = payload.get("event", {})
    if event.get("type") == "app_mention":
        text = str(event.get("text", "")).strip()
        user_id = event.get("user")
        channel_id = event.get("channel")
        response_text = _handle_topic_command(_strip_bot_mention(text), user_id=user_id, user_name=None, channel_id=channel_id, background_tasks=background_tasks)
        if not response_text.startswith("Processing your request:"):
            _post_event_response(channel_id=channel_id, user_id=user_id, text=response_text)
    return {"ok": True}


def _handle_topic_command(
    text: str,
    user_id: str | None,
    user_name: str | None,
    channel_id: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> str:
    text = _normalize_command_text(text)
    command, _, topic = text.partition(" ")
    command = command.casefold().strip()
    topic = topic.strip()

    if command in {"help", ""}:
        return "Use `add <topic>`, `add topic <topic>`, `track <topic>`, `remove <topic>`, `list`, `fetch news`, or natural language like `fetch latest articles about EU AI Act compliance`."

    if command == "fetch" and topic.casefold() == "news":
        return _run_with_processing_lock(channel_id, user_id, text, lambda: _fetch_news_for_active_topics(), background_tasks=background_tasks)

    with db_session() as session:
        if command == "add":
            if not topic:
                return "Please include a topic, for example: `add AI startup funding`."
            is_allowed, error = validate_professional_ai_topic(topic)
            if not is_allowed:
                return error or "Topic rejected."
            row, changed = add_search_topic(session, topic, slack_user_id=user_id, slack_user_name=user_name)
            if changed:
                return f"Added topic #{row.id}: `{row.topic}`"
            return f"Topic already active: `{row.topic}`"

        if command == "remove":
            if not topic:
                return "Please include a topic, for example: `remove AI startup funding`."
            row = remove_search_topic(session, topic, slack_user_id=user_id, slack_user_name=user_name)
            if not row:
                return f"Topic not found: `{topic}`"
            return f"Removed topic #{row.id}: `{row.topic}`"

        if command == "list":
            topics = list_active_search_topics(session)
            if not topics:
                return "No active topics yet. Use `add <topic>` to add one."
            lines = [f"#{topic_row.id}: {topic_row.topic}" for topic_row in topics]
            return "Active topics:\n" + "\n".join(lines)

    natural_topic = extract_news_topic(text)
    if natural_topic:
        return _run_with_processing_lock(channel_id, user_id, text, lambda: _fetch_news_for_topic(natural_topic), background_tasks=background_tasks)

    return "Unknown command. Use `add <topic>`, `track <topic>`, `remove <topic>`, `list`, `fetch news`, or ask `fetch latest articles about <AI/compliance topic>`."


def _run_with_processing_lock(
    channel_id: str | None,
    user_id: str | None,
    request_text: str,
    work: Callable[[], str],
    background_tasks: BackgroundTasks | None = None,
) -> str:
    if not channel_id or not user_id:
        return work()

    with db_session() as session:
        lock = acquire_slack_processing_lock(session, channel_id, user_id, request_text)
        if not lock:
            return "A request is already running for you in this channel. Please wait until it finishes."
        lock_id = lock.id

    processing_ts = _post_processing_message(channel_id, user_id, request_text)
    if processing_ts:
        with db_session() as session:
            update_slack_processing_message(session, lock_id, processing_ts)

    if background_tasks is not None:
        background_tasks.add_task(_complete_processing_request, channel_id, user_id, lock_id, processing_ts, work)
        return f"Processing your request: {request_text}"

    return _complete_processing_request(channel_id, user_id, lock_id, processing_ts, work)


def _complete_processing_request(channel_id: str, user_id: str, lock_id: int, processing_ts: str | None, work: Callable[[], str]) -> str:
    try:
        result = work()
        if processing_ts:
            _update_processing_message(channel_id, processing_ts, result)
        else:
            _post_event_response(channel_id=channel_id, user_id=user_id, text=result)
        return result
    finally:
        with db_session() as session:
            release_slack_processing_lock_for_user(session, channel_id, user_id)


def _post_processing_message(channel_id: str, user_id: str, request_text: str) -> str | None:
    if not settings.slack_bot_token:
        return None
    text = f"Processing your request: {request_text}"
    try:
        response = SlackWebClient(settings.slack_bot_token).post_ephemeral(channel_id=channel_id, user_id=user_id, text=text)
        return response.get("message_ts") or response.get("ts")
    except Exception:
        return None


def _update_processing_message(channel_id: str, message_ts: str, result_text: str) -> None:
    if not settings.slack_bot_token:
        return
    try:
        SlackWebClient(settings.slack_bot_token).update_message(channel_id=channel_id, message_ts=message_ts, text=result_text)
    except Exception:
        return


def _normalize_command_text(text: str) -> str:
    stripped = " ".join(text.strip().split())
    lowered = stripped.casefold()
    for prefix in ("add topic ", "track topic ", "monitor topic "):
        if lowered.startswith(prefix):
            return "add " + stripped[len(prefix) :]
    for prefix in ("track ", "monitor "):
        if lowered.startswith(prefix):
            return "add " + stripped[len(prefix) :]
    for prefix in ("delete topic ", "remove topic ", "stop tracking "):
        if lowered.startswith(prefix):
            return "remove " + stripped[len(prefix) :]
    return stripped


def _fetch_news_for_topic(topic: str) -> str:
    topic = clean_search_topic(topic)
    is_allowed, error = validate_professional_ai_topic(topic)
    if not is_allowed:
        return error or "Topic rejected."

    result = run_news_pipeline_now(topic, settings.default_time_window_hours, settings.max_stories_per_run)
    warning_count = len(result.get("errors", []))
    warning_text = f", {warning_count} warning{'s' if warning_count != 1 else ''}" if warning_count else ""
    return (
        "Fetched latest news and articles:\n"
        f"- `{topic}`: {result['status']}, "
        f"{result['discovered_sources_count']} sources, "
        f"{result.get('duplicate_sources_skipped', 0)} duplicates skipped, "
        f"{result.get('selected_candidates_count', 0)} relevant, "
        f"{len(result.get('slack_messages', []))} Slack approval messages"
        f"{warning_text}"
    )


def _fetch_news_for_active_topics() -> str:
    with db_session() as session:
        topics = list_active_search_topics(session)

    if not topics:
        return "No active topics yet. Use `add <topic>` before `fetch news`."

    summaries = []
    for topic_row in topics:
        summaries.append(_fetch_news_for_topic(topic_row.topic).split("\n", 1)[1])
    return "Fetched latest news:\n" + "\n".join(summaries)


def _post_event_response(channel_id: str | None, user_id: str | None, text: str) -> None:
    if not channel_id or not user_id or not settings.slack_bot_token:
        return
    try:
        SlackWebClient(settings.slack_bot_token).post_ephemeral(channel_id=channel_id, user_id=user_id, text=text)
    except Exception:
        SlackWebClient(settings.slack_bot_token).post_message(channel_id=channel_id, text=text)


def _strip_bot_mention(text: str) -> str:
    parts = text.split(maxsplit=1)
    if parts and parts[0].startswith("<@"):
        return parts[1] if len(parts) > 1 else ""
    return text
