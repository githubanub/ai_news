import asyncio
import logging

import httpx

from app.config import settings
from app.db import db_session
from app.repositories import list_active_search_topics


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def trigger_pipeline(topic: str) -> None:
    url = f"{settings.scheduler_api_base_url.rstrip('/')}/jobs/run-news-pipeline"
    payload = {
        "topic": topic,
        "time_window_hours": settings.default_time_window_hours,
        "max_stories": settings.max_stories_per_run,
        "skip_duplicate_check": False,
    }
    async with httpx.AsyncClient(timeout=settings.scheduler_request_timeout_seconds) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        logger.info("Triggered news pipeline for topic=%r: %s", topic, response.json())


def get_scheduler_topics() -> list[str]:
    with db_session() as session:
        topics = [topic.topic for topic in list_active_search_topics(session)]
    return topics or [settings.scheduler_topic]


async def run_scheduler() -> None:
    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled. Set SCHEDULER_ENABLED=true to run it.")
        return

    interval_seconds = max(60, settings.scheduler_interval_minutes * 60)
    logger.info(
        "Scheduler started: topic=%r interval_minutes=%s api_base_url=%s",
        settings.scheduler_topic,
        settings.scheduler_interval_minutes,
        settings.scheduler_api_base_url,
    )
    while True:
        try:
            for topic in get_scheduler_topics():
                await trigger_pipeline(topic)
        except Exception:
            logger.exception("Scheduled pipeline trigger failed")
        await asyncio.sleep(interval_seconds)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
