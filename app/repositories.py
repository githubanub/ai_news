import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import NewsArticle, NewsRun, SearchTopic, SlackDecision, SlackProcessingLock


def create_run(session: Session, run_id: str, topic: str, time_window_hours: int, max_stories: int) -> NewsRun:
    run = NewsRun(id=run_id, topic=topic, time_window_hours=time_window_hours, max_stories=max_stories, status="started", errors=[])
    session.add(run)
    return run


def complete_run(session: Session, run_id: str, status: str, errors: list[dict[str, Any]]) -> None:
    run = session.get(NewsRun, run_id)
    if run:
        run.status = status
        run.errors = errors


def store_run_draft(session: Session, run_id: str, draft: dict[str, Any]) -> None:
    run = session.get(NewsRun, run_id)
    if run:
        run.draft_title = draft.get("title")
        run.draft_body = draft.get("body")
        run.draft_metadata = {
            "citations": draft.get("citations", []),
            "source_count": draft.get("source_count"),
            "generated_by": draft.get("generated_by"),
        }


def filter_new_sources(session: Session, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    urls = [source["url"] for source in sources if source.get("url")]
    normalized_headlines = {_normalize_headline(source.get("title")) for source in sources if source.get("title")}
    normalized_headlines.discard("")
    if not urls and not normalized_headlines:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.duplicate_lookback_days)
    existing_articles = session.scalars(
        select(NewsArticle).where(
            NewsArticle.created_at >= cutoff,
        )
    ).all()
    existing_urls = {article.url for article in existing_articles if article.url in urls}
    existing_headlines = {
        _normalize_headline(article.title)
        for article in existing_articles
        if _normalize_headline(article.title) in normalized_headlines
    }

    return [
        source
        for source in sources
        if source.get("url") not in existing_urls
        and _normalize_headline(source.get("title")) not in existing_headlines
    ]


def _normalize_headline(headline: str | None) -> str:
    if not headline:
        return ""
    normalized = headline.casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_topic(topic: str | None) -> str:
    return _normalize_headline(topic)


def add_search_topic(
    session: Session,
    topic: str,
    slack_user_id: str | None = None,
    slack_user_name: str | None = None,
) -> tuple[SearchTopic, bool]:
    normalized_topic = normalize_topic(topic)
    existing = session.scalar(select(SearchTopic).where(SearchTopic.normalized_topic == normalized_topic))
    if existing:
        was_inactive = not existing.is_active
        existing.topic = topic.strip()
        existing.is_active = True
        existing.created_by_slack_user_id = slack_user_id or existing.created_by_slack_user_id
        existing.created_by_slack_user_name = slack_user_name or existing.created_by_slack_user_name
        return existing, was_inactive

    row = SearchTopic(
        topic=topic.strip(),
        normalized_topic=normalized_topic,
        is_active=True,
        created_by_slack_user_id=slack_user_id,
        created_by_slack_user_name=slack_user_name,
    )
    session.add(row)
    session.flush()
    return row, True


def remove_search_topic(
    session: Session,
    topic: str,
    slack_user_id: str | None = None,
    slack_user_name: str | None = None,
) -> SearchTopic | None:
    normalized_topic = normalize_topic(topic)
    existing = session.scalar(select(SearchTopic).where(SearchTopic.normalized_topic == normalized_topic))
    if not existing:
        return None
    existing.is_active = False
    existing.removed_by_slack_user_id = slack_user_id
    existing.removed_by_slack_user_name = slack_user_name
    return existing


def list_active_search_topics(session: Session) -> list[SearchTopic]:
    return session.scalars(select(SearchTopic).where(SearchTopic.is_active.is_(True)).order_by(SearchTopic.created_at.asc())).all()


def store_articles(session: Session, run_id: str, articles: list[dict[str, Any]], allow_duplicate_articles: bool = False) -> list[NewsArticle]:
    stored = []
    existing_articles = session.scalars(select(NewsArticle)).all()
    existing_urls = {article.url for article in existing_articles}
    existing_headlines = {_normalize_headline(article.title) for article in existing_articles}
    for article in articles:
        url = article.get("url")
        title = article.get("title")
        if not url or not title:
            continue

        normalized_title = _normalize_headline(title)
        is_duplicate = url in existing_urls or normalized_title in existing_headlines
        if not allow_duplicate_articles and is_duplicate:
            continue
        stored_url = f"{url}#manual-run-{run_id}" if allow_duplicate_articles and url in existing_urls else url

        row = NewsArticle(
            run_id=run_id,
            provider=article.get("provider"),
            title=title,
            url=stored_url,
            source_name=article.get("source_name"),
            published_at=article.get("published_at"),
            snippet=article.get("snippet") or article.get("summary"),
            thumbnail_url=article.get("thumbnail_url"),
            relevance_score=article.get("relevance_score"),
            status="pending_approval",
            raw={**article, "source_url": url} if stored_url != url else article,
        )
        session.add(row)
        stored.append(row)
        existing_urls.add(stored_url)
        existing_headlines.add(normalized_title)
    session.flush()
    return stored


def update_article_slack_message(session: Session, article_id: int, channel_id: str | None, message_ts: str | None) -> None:
    article = session.get(NewsArticle, article_id)
    if article:
        article.slack_channel_id = channel_id
        article.slack_message_ts = message_ts


def record_slack_decision(
    session: Session,
    run_id: str,
    article_id: int | None,
    action: str,
    slack_user_id: str | None,
    slack_user_name: str | None,
    slack_channel_id: str | None,
    slack_message_ts: str | None,
    raw_payload: dict[str, Any],
) -> SlackDecision:
    decision = SlackDecision(
        run_id=run_id,
        article_id=article_id,
        action=action,
        slack_user_id=slack_user_id,
        slack_user_name=slack_user_name,
        slack_channel_id=slack_channel_id,
        slack_message_ts=slack_message_ts,
        raw_payload=raw_payload,
    )
    session.add(decision)

    if article_id is not None:
        article = session.get(NewsArticle, article_id)
        if article:
            article.status = action

    return decision


def acquire_slack_processing_lock(
    session: Session,
    channel_id: str,
    user_id: str,
    request_text: str,
) -> SlackProcessingLock | None:
    session.flush()
    expire_stale_slack_processing_locks(session)
    existing = session.scalar(
        select(SlackProcessingLock).where(
            SlackProcessingLock.channel_id == channel_id,
            SlackProcessingLock.user_id == user_id,
        )
    )
    if existing:
        if existing.status == "running":
            return None
        existing.status = "running"
        existing.request_text = request_text
        existing.processing_message_ts = None
        session.flush()
        return existing

    lock = SlackProcessingLock(channel_id=channel_id, user_id=user_id, request_text=request_text, status="running")
    session.add(lock)
    session.flush()
    return lock


def update_slack_processing_message(session: Session, lock_id: int, message_ts: str | None) -> None:
    lock = session.get(SlackProcessingLock, lock_id)
    if lock:
        lock.processing_message_ts = message_ts


def release_slack_processing_lock(session: Session, lock_id: int) -> None:
    lock = session.get(SlackProcessingLock, lock_id)
    if lock:
        lock.status = "completed"


def release_slack_processing_lock_for_user(session: Session, channel_id: str, user_id: str) -> None:
    lock = session.scalar(
        select(SlackProcessingLock).where(
            SlackProcessingLock.channel_id == channel_id,
            SlackProcessingLock.user_id == user_id,
            SlackProcessingLock.status == "running",
        )
    )
    if lock:
        lock.status = "completed"
        session.flush()


def expire_stale_slack_processing_locks(session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.slack_processing_lock_timeout_minutes)
    locks = session.scalars(
        select(SlackProcessingLock).where(
            SlackProcessingLock.status == "running",
            SlackProcessingLock.updated_at < cutoff,
        )
    ).all()
    for lock in locks:
        lock.status = "expired"
    if locks:
        session.flush()
    return len(locks)
