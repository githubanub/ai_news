from uuid import uuid4

from app.db import db_session, init_db
from app.repositories import acquire_slack_processing_lock, create_run, filter_new_sources, release_slack_processing_lock_for_user, store_articles


def test_filter_new_sources_skips_duplicate_headlines():
    init_db()
    run_id = str(uuid4())
    unique_suffix = str(uuid4())
    headline = f"AI Startup Raises Seed Round {unique_suffix}!"
    with db_session() as session:
        create_run(session, run_id, "AI funding", 24, 5)
        stored = store_articles(
            session,
            run_id,
            [
                {
                    "title": headline,
                    "url": f"https://example.com/original-{unique_suffix}",
                    "provider": "test",
                }
            ],
        )
        assert stored[0].id is not None
        assert stored[0].title == headline

    with db_session() as session:
        new_sources = filter_new_sources(
            session,
            [
                {
                    "title": headline.casefold().replace("!", ""),
                    "url": f"https://example.com/different-url-{unique_suffix}",
                    "provider": "test",
                },
                {
                    "title": f"Different AI funding story {unique_suffix}",
                    "url": f"https://example.com/different-story-{unique_suffix}",
                    "provider": "test",
                },
            ],
        )

    assert [source["title"] for source in new_sources] == [f"Different AI funding story {unique_suffix}"]


def test_store_articles_can_allow_duplicate_articles_for_manual_runs():
    init_db()
    unique_suffix = str(uuid4())
    first_run_id = str(uuid4())
    second_run_id = str(uuid4())
    article = {
        "title": f"FDA AI medical software update {unique_suffix}",
        "url": f"https://example.com/fda-ai-{unique_suffix}",
        "provider": "test",
    }

    with db_session() as session:
        create_run(session, first_run_id, "FDA AI medical software", 24, 5)
        create_run(session, second_run_id, "FDA AI medical software", 24, 5)
        first = store_articles(session, first_run_id, [article])
        skipped = store_articles(session, second_run_id, [article])
        duplicated = store_articles(session, second_run_id, [article], allow_duplicate_articles=True)

    assert len(first) == 1
    assert skipped == []
    assert len(duplicated) == 1


def test_slack_processing_lock_blocks_same_user_until_release():
    init_db()
    channel_id = f"C{uuid4()}"
    user_id = f"U{uuid4()}"

    with db_session() as session:
        first = acquire_slack_processing_lock(session, channel_id, user_id, "fetch news")
        second = acquire_slack_processing_lock(session, channel_id, user_id, "fetch news again")
        assert first is not None
        assert second is None

    with db_session() as session:
        release_slack_processing_lock_for_user(session, channel_id, user_id)
        third = acquire_slack_processing_lock(session, channel_id, user_id, "fetch news later")
        assert third is not None
        release_slack_processing_lock_for_user(session, channel_id, user_id)
