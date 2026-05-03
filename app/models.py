from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NewsRun(Base):
    __tablename__ = "news_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="started")
    time_window_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    max_stories: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    articles: Mapped[list["NewsArticle"]] = relationship(back_populates="run")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("url", name="uq_news_articles_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("news_runs.id"), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="discovered")
    slack_channel_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slack_message_ts: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    run: Mapped[NewsRun] = relationship(back_populates="articles")
    approvals: Mapped[list["SlackDecision"]] = relationship(back_populates="article")


class SlackDecision(Base):
    __tablename__ = "slack_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("news_runs.id"), nullable=False, index=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("news_articles.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    slack_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slack_user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_channel_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slack_message_ts: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    article: Mapped[NewsArticle | None] = relationship(back_populates="approvals")


class SearchTopic(Base):
    __tablename__ = "search_topics"
    __table_args__ = (UniqueConstraint("normalized_topic", name="uq_search_topics_normalized_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_topic: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by_slack_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_slack_user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    removed_by_slack_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    removed_by_slack_user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class SlackProcessingLock(Base):
    __tablename__ = "slack_processing_locks"
    __table_args__ = (UniqueConstraint("channel_id", "user_id", name="uq_slack_processing_lock_channel_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    request_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_message_ts: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
