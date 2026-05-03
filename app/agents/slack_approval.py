from app.graphs.news_state import NewsPipelineState
from app.config import settings
from app.db import db_session
from app.integrations.slack_web_client import SlackWebClient
from app.repositories import store_articles, update_article_slack_message
from app.services.draft_formatter import slack_excerpt


def slack_approval_node(state: NewsPipelineState) -> NewsPipelineState:
    if not settings.slack_bot_token or not settings.slack_approval_channel_id:
        state.setdefault("errors", []).append({"node": "slack_approval", "message": "Slack bot token or approval channel is not configured"})
        return state

    if not state.get("selected_candidates"):
        state["approval_status"] = "needs_edit"
        return state

    candidates = state.get("selected_candidates", [])
    if not state.get("technical_blog_draft"):
        state.setdefault("errors", []).append({"node": "slack_approval", "message": "No draft available for approval"})
        return state

    run_id = state.get("run_id", "")
    client = SlackWebClient(settings.slack_bot_token)
    posted_messages = []
    with db_session() as session:
        stored_articles = store_articles(session, run_id, candidates, allow_duplicate_articles=state.get("skip_duplicate_check", False))
        article_id = stored_articles[0].id if stored_articles else None
        draft = state["technical_blog_draft"]
        text = f"Approval requested for generated article: {draft.get('title')}"
        blocks = _build_approval_blocks(
            run_id=run_id,
            article_id=article_id,
            title=draft.get("title", "Generated AI news article"),
            summary=_build_draft_summary(draft),
            source_count=len(candidates),
            preview_url=_build_preview_url(run_id),
        )
        try:
            response = client.post_message(settings.slack_approval_channel_id, text=text, blocks=blocks)
        except Exception as exc:
            state.setdefault("errors", []).append({"node": "slack_approval", "message": str(exc), "article_id": article_id})
            return state
        for article in stored_articles:
            update_article_slack_message(session, article.id, response.get("channel"), response.get("ts"))
        posted_messages.append({"article_id": article_id, "channel": response.get("channel"), "ts": response.get("ts")})

    if not posted_messages:
        state.setdefault("errors", []).append({"node": "slack_approval", "message": "No Slack approval messages were posted"})
        return state

    state["slack_messages"] = posted_messages
    state["approval_status"] = "pending"
    state["slack_channel_id"] = posted_messages[0].get("channel")
    state["slack_message_ts"] = posted_messages[0].get("ts")
    return state


def _build_approval_blocks(run_id: str, article_id: int | None, title: str, summary: str, source_count: int, preview_url: str | None) -> list[dict]:
    action_value = f"{run_id}:{article_id}"
    fields = [{"type": "mrkdwn", "text": f"*Run ID:*\n{run_id}"}, {"type": "mrkdwn", "text": f"*Sources analyzed:*\n{source_count}"}]

    elements = [
        {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "style": "primary", "action_id": "approve_article", "value": action_value},
        {"type": "button", "text": {"type": "plain_text", "text": "Needs edit"}, "action_id": "needs_edit_article", "value": action_value},
        {"type": "button", "text": {"type": "plain_text", "text": "Reject"}, "style": "danger", "action_id": "reject_article", "value": action_value},
    ]
    if preview_url:
        elements.insert(0, {"type": "button", "text": {"type": "plain_text", "text": "Open full draft"}, "url": preview_url, "action_id": "open_full_draft", "value": action_value})

    return [
        {"type": "header", "text": {"type": "plain_text", "text": "AI news draft approval", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary or "Draft generated from discovered sources."}},
        {"type": "section", "fields": fields},
        {
            "type": "actions",
            "elements": elements,
        },
    ]


def _build_draft_summary(draft: dict) -> str:
    return slack_excerpt(str(draft.get("body") or ""))


def _build_preview_url(run_id: str) -> str | None:
    base_url = (settings.app_public_base_url or settings.scheduler_api_base_url).rstrip("/")
    if not base_url:
        return None
    return f"{base_url}/articles/{run_id}/preview"
