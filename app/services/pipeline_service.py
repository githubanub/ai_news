from uuid import uuid4

from app.db import db_session
from app.graphs.news_graph import news_graph
from app.repositories import complete_run, create_run, store_run_draft


def run_news_pipeline_now(topic: str, time_window_hours: int, max_stories: int, skip_duplicate_check: bool = True) -> dict:
    run_id = str(uuid4())
    with db_session() as session:
        create_run(session, run_id, topic, time_window_hours, max_stories)

    state = news_graph.invoke(
        {
            "run_id": run_id,
            "topic": topic,
            "time_window_hours": time_window_hours,
            "max_stories": max_stories,
            "skip_duplicate_check": skip_duplicate_check,
            "errors": [],
            "audit_events": [],
        }
    )
    errors = state.get("errors", [])
    if state.get("slack_message_ts"):
        status = "pending_approval"
    elif errors and not state.get("discovered_sources"):
        status = "failed"
    elif errors:
        status = "completed_with_warnings"
    else:
        status = "completed"

    with db_session() as session:
        store_run_draft(session, run_id, state.get("technical_blog_draft", {}))
        complete_run(session, run_id, status, errors)

    draft = state.get("technical_blog_draft", {})
    return {
        "run_id": run_id,
        "topic": topic,
        "status": status,
        "discovered_sources_count": len(state.get("discovered_sources", [])),
        "duplicate_sources_skipped": state.get("duplicate_sources_skipped", 0),
        "skip_duplicate_check": skip_duplicate_check,
        "selected_candidates_count": len(state.get("selected_candidates", [])),
        "discovered_sources": state.get("discovered_sources", []),
        "selected_story": state.get("selected_story"),
        "draft_title": draft.get("title"),
        "approval_status": state.get("approval_status"),
        "slack_channel_id": state.get("slack_channel_id"),
        "slack_message_ts": state.get("slack_message_ts"),
        "slack_messages": state.get("slack_messages", []),
        "errors": errors,
    }
