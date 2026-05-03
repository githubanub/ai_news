from uuid import uuid4

from app.db import db_session, init_db
from app.repositories import add_search_topic, list_active_search_topics, remove_search_topic


def test_add_remove_and_reactivate_topic():
    init_db()
    topic = f"test topic {uuid4()}"

    with db_session() as session:
        row, changed = add_search_topic(session, topic, slack_user_id="U123", slack_user_name="anubhaw")
        topic_id = row.id

    assert changed is True
    assert topic_id is not None

    with db_session() as session:
        row, changed = add_search_topic(session, topic.upper(), slack_user_id="U123", slack_user_name="anubhaw")

    assert changed is False
    assert row.id == topic_id

    with db_session() as session:
        removed = remove_search_topic(session, topic, slack_user_id="U456", slack_user_name="reviewer")

    assert removed is not None
    assert removed.is_active is False
    assert removed.removed_by_slack_user_id == "U456"

    with db_session() as session:
        active_topics = [row.topic for row in list_active_search_topics(session)]

    assert topic.upper() not in active_topics

    with db_session() as session:
        row, changed = add_search_topic(session, topic, slack_user_id="U123", slack_user_name="anubhaw")

    assert changed is True
    assert row.id == topic_id
    assert row.is_active is True

    with db_session() as session:
        remove_search_topic(session, topic, slack_user_id="U456", slack_user_name="reviewer")
