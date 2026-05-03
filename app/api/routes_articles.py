from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.db import db_session
from app.models import NewsArticle, NewsRun, SearchTopic, SlackDecision
from app.services.draft_formatter import clean_draft_text

router = APIRouter()


@router.get("/")
async def list_articles(limit: int = 50) -> list[dict]:
    with db_session() as session:
        articles = session.scalars(select(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(limit)).all()
        return [
            {
                "id": article.id,
                "run_id": article.run_id,
                "title": article.title,
                "url": article.url,
                "source_name": article.source_name,
                "status": article.status,
                "slack_channel_id": article.slack_channel_id,
                "slack_message_ts": article.slack_message_ts,
                "created_at": article.created_at.isoformat(),
            }
            for article in articles
        ]


@router.get("/runs")
async def list_runs(limit: int = 50) -> list[dict]:
    with db_session() as session:
        runs = session.scalars(select(NewsRun).order_by(NewsRun.created_at.desc()).limit(limit)).all()
        return [
            {
                "id": run.id,
                "topic": run.topic,
                "status": run.status,
                "time_window_hours": run.time_window_hours,
                "max_stories": run.max_stories,
                "errors": run.errors,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ]


@router.get("/decisions")
async def list_decisions(limit: int = 50) -> list[dict]:
    with db_session() as session:
        decisions = session.scalars(select(SlackDecision).order_by(SlackDecision.created_at.desc()).limit(limit)).all()
        return [
            {
                "id": decision.id,
                "run_id": decision.run_id,
                "article_id": decision.article_id,
                "action": decision.action,
                "slack_user_id": decision.slack_user_id,
                "slack_user_name": decision.slack_user_name,
                "slack_channel_id": decision.slack_channel_id,
                "slack_message_ts": decision.slack_message_ts,
                "created_at": decision.created_at.isoformat(),
            }
            for decision in decisions
        ]


@router.get("/topics")
async def list_topics(include_inactive: bool = False) -> list[dict]:
    with db_session() as session:
        query = select(SearchTopic).order_by(SearchTopic.created_at.asc())
        if not include_inactive:
            query = query.where(SearchTopic.is_active.is_(True))
        topics = session.scalars(query).all()
        return [
            {
                "id": topic.id,
                "topic": topic.topic,
                "is_active": topic.is_active,
                "created_by_slack_user_id": topic.created_by_slack_user_id,
                "created_by_slack_user_name": topic.created_by_slack_user_name,
                "removed_by_slack_user_id": topic.removed_by_slack_user_id,
                "removed_by_slack_user_name": topic.removed_by_slack_user_name,
                "created_at": topic.created_at.isoformat(),
            }
            for topic in topics
        ]


@router.get("/{draft_id}/preview")
async def preview_draft(draft_id: str) -> HTMLResponse:
    with db_session() as session:
        run = session.get(NewsRun, draft_id)
        if not run or not run.draft_body:
            raise HTTPException(status_code=404, detail="Draft not found")
        body = _render_markdownish(run.draft_body)
        html = f"""
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{_escape(run.draft_title or "AI news draft")}</title>
            <style>
              body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; max-width: 860px; margin: 40px auto; padding: 0 20px; color: #17202a; }}
              h1 {{ font-size: 32px; line-height: 1.2; }}
              p {{ font-size: 17px; }}
              .meta {{ color: #637083; font-size: 14px; margin-bottom: 28px; }}
            </style>
          </head>
          <body>
            <h1>{_escape(run.draft_title or "AI news draft")}</h1>
            <div class="meta">Run ID: {_escape(run.id)} · Topic: {_escape(run.topic)}</div>
            {body}
          </body>
        </html>
        """
        return HTMLResponse(html)


def _render_markdownish(text: str) -> str:
    blocks = []
    for part in clean_draft_text(text).split("\n\n"):
        part = part.strip()
        if not part:
            continue
        escaped = _escape(part)
        if _looks_like_heading(part):
            blocks.append(f"<h2>{escaped}</h2>")
        elif part.startswith("- "):
            items = [_escape(line[2:].strip()) for line in part.splitlines() if line.startswith("- ")]
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>")
        else:
            blocks.append(f"<p>{escaped.replace(chr(10), '<br>')}</p>")
    return "\n".join(blocks)


def _looks_like_heading(value: str) -> bool:
    return len(value) <= 80 and "\n" not in value and value.endswith(":")


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
