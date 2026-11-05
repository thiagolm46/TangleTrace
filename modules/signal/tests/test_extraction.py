from __future__ import annotations

from discord_data.extraction import MESSAGE_SCHEMA, transform_message


def test_transform_message_preserves_native_interaction_fields() -> None:
    row = transform_message(
        {
            "id": "message-1",
            "channel_id": "channel-1",
            "channel_name": "help",
            "author": {
                "id": "author-1",
                "username": "alice",
                "discriminator": "1234",
                "bot": False,
            },
            "timestamp": "2026-01-01T00:00:00.000Z",
            "type": 19,
            "content": "Thanks",
            "webhook_id": "webhook-1",
            "thread": {"id": "thread-1"},
            "reactions": [{"emoji": {"name": "thumbsup"}, "count": 2}],
            "attachments": [{"id": "attachment-1"}],
            "embeds": [{"type": "rich"}],
            "mentions": [{"id": "author-2"}],
            "message_reference": {"message_id": "parent-1", "guild_id": "guild-1"},
        },
        "guild-1",
        {"guild-1": {"name": "Neo4j", "positive_score": 7}},
    )

    assert row["native_thread_id"] == "thread-1"
    assert row["webhook_id"] == "webhook-1"
    assert row["reaction_count"] == 1
    assert row["reactions_json"] == '[{"emoji":{"name":"thumbsup"},"count":2}]'
    assert row["attachments_json"] == '[{"id":"attachment-1"}]'
    assert {"native_thread_id", "webhook_id", "reactions_json"}.issubset(
        MESSAGE_SCHEMA.names
    )