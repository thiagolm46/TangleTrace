"""Fully synthetic demonstration data with no corpus information."""
import csv
import json


def create_demo(root):
    folder = root / "demo"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "annotation_windows.csv"
    if path.exists():
        return path
    specs = [
        ("P01", "Alex", "Has anyone used pytest with an in-memory database?", False),
        ("P02", "Blake", "I have a problem with the Docker build.", False),
        ("P03", "Casey", "Alex, use a fixture to recreate the database for each test.", True),
        ("P04", "Bot", "Build #42 completed.", False),
        ("P05", "Dana", "Blake, what message appears in the log?", True),
        ("P06", "Alex", "Thanks, Casey! I will try the fixture.", True),
        ("P07", "Blake", "The error is 'permission denied' when copying the file.", True),
        ("P08", "Casey", "Also run rollback when the test finishes.", True),
        ("P09", "Dana", "Check the container user and directory permissions.", True),
        ("P10", "Alex", "The fixture and rollback solved it. Thanks for both examples!", True),
        ("P11", "Evan", "Changing the subject: the new project version was released.", True),
        ("P12", "Blake", "It was the container user. It worked!", True),
    ]
    messages = []
    for i, (mid, author, content, target) in enumerate(specs, 1):
        messages.append({"message_id": mid, "guild_id": "demo-guild", "server_id": "demo-guild",
                         "guild_name": "Example community", "channel_id": "demo-channel",
                         "channel_name": "development", "author_id": author, "author_username": author,
                         "timestamp": f"2026-10-19T10:{i:02d}:00+00:00", "content": content,
                         "sequence": i, "window_role": "annotated" if target else "context",
                         "requires_reply_annotation": target, "is_bot": author == "Bot",
                         "native_reply_to_message_id": "P03" if mid == "P06" else None,
                         "native_reply_evidence": "positive_observed" if mid == "P06" else "unknown",
                         "native_available_fields": ["message_id", "content", "author_id", "timestamp", "is_bot"],
                         "attachments": [], "embeds": [], "mentions": [], "reactions": []})
    fields = ["annotation_id", "window_id", "guild_id", "channel_id", "guild_name", "channel_name", "period",
              "annotated_message_count", "context_message_count", "messages_json", "human_reply_edges_json", "human_reply_source_statuses_json"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"annotation_id": "DEMO_001", "window_id": "DEMO_001", "guild_id": "demo-guild",
                         "channel_id": "demo-channel", "guild_name": "Example community", "channel_name": "development",
                         "period": "2026-10", "annotated_message_count": 9, "context_message_count": 3,
                         "messages_json": json.dumps(messages, ensure_ascii=False), "human_reply_edges_json": "[]",
                         "human_reply_source_statuses_json": "[]"})
    return path
