from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    if not database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(news_runs)")).all()}
        migrations = {
            "draft_title": "ALTER TABLE news_runs ADD COLUMN draft_title TEXT",
            "draft_body": "ALTER TABLE news_runs ADD COLUMN draft_body TEXT",
            "draft_metadata": "ALTER TABLE news_runs ADD COLUMN draft_metadata JSON",
        }
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(text(statement))
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS slack_processing_locks ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "channel_id VARCHAR(100) NOT NULL, "
                "user_id VARCHAR(100) NOT NULL, "
                "status VARCHAR(50) NOT NULL, "
                "request_text TEXT, "
                "processing_message_ts VARCHAR(100), "
                "created_at DATETIME NOT NULL, "
                "updated_at DATETIME NOT NULL, "
                "CONSTRAINT uq_slack_processing_lock_channel_user UNIQUE (channel_id, user_id)"
                ")"
            )
        )


@contextmanager
def db_session() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
