from uuid import uuid4
from urllib.parse import quote

from fastapi import BackgroundTasks

from app.api.routes_slack import _handle_topic_command, _run_with_processing_lock
from app.db import db_session
from app.repositories import release_slack_processing_lock_for_user
from fastapi.testclient import TestClient

from app.main import app


def test_slack_topic_command_list_after_add():
    topic = f"AI governance compliance topic {uuid4()}"

    add_response = _handle_topic_command(f"add {topic}", user_id="U123", user_name="anubhaw")
    list_response = _handle_topic_command("list", user_id="U123", user_name="anubhaw")
    remove_response = _handle_topic_command(f"remove {topic}", user_id="U123", user_name="anubhaw")

    assert "Added topic" in add_response
    assert topic in list_response
    assert "Removed topic" in remove_response


def test_slack_action_form_payload_does_not_require_multipart(monkeypatch):
    async def fake_verify_slack_signature(request, signing_secret):
        _ = signing_secret
        return await request.body()

    monkeypatch.setattr("app.api.routes_slack.verify_slack_signature", fake_verify_slack_signature)
    payload = quote('{"actions":[{"action_id":"reject_article","value":"run-1:1"}],"user":{"id":"U123"},"channel":{"id":"C123"},"message":{"ts":"1.23"}}')

    response = TestClient(app).post(
        "/webhooks/slack/actions",
        content=f"payload={payload}",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_natural_language_non_ai_topic_is_rejected():
    response = _handle_topic_command("fetch latest articles about celebrity gossip", user_id="U123", user_name="anubhaw")

    assert "Topic rejected" in response


def test_app_mention_supports_track_topic_aliases():
    topic = f"AI compliance monitoring {uuid4()}"

    add_response = _handle_topic_command(f"track topic {topic}", user_id="U123", user_name="anubhaw")
    remove_response = _handle_topic_command(f"stop tracking {topic}", user_id="U123", user_name="anubhaw")

    assert "Added topic" in add_response
    assert "Removed topic" in remove_response


def test_fetch_work_is_deferred_when_background_tasks_are_available(monkeypatch):
    channel_id = f"C-{uuid4()}"
    user_id = f"U-{uuid4()}"
    calls = {"work": 0}

    monkeypatch.setattr("app.api.routes_slack._post_processing_message", lambda channel_id, user_id, request_text: None)

    def work():
        calls["work"] += 1
        return "done"

    background_tasks = BackgroundTasks()
    response = _run_with_processing_lock(channel_id, user_id, "fetch latest AI governance news", work, background_tasks=background_tasks)

    try:
        assert response == "Processing your request: fetch latest AI governance news"
        assert calls["work"] == 0
        assert len(background_tasks.tasks) == 1
    finally:
        with db_session() as session:
            release_slack_processing_lock_for_user(session, channel_id, user_id)
