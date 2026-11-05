"""Transform the raw archive and safely write messages to Parquet."""

from __future__ import annotations

import json
import re
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

MESSAGE_SCHEMA = pa.schema(
    [
        pa.field("guild_id", pa.string()),
        pa.field("guild_name", pa.string()),
        pa.field("message_id", pa.string()),
        pa.field("channel_id", pa.string()),
        pa.field("channel_name", pa.string()),
        pa.field("author_id", pa.string()),
        pa.field("author_username", pa.string()),
        pa.field("author_discriminator", pa.string()),
        pa.field("webhook_id", pa.string()),
        pa.field("timestamp", pa.string()),
        pa.field("edited_timestamp", pa.string()),
        pa.field("message_type", pa.int64()),
        pa.field("native_thread_id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("content_length", pa.int64()),
        pa.field("is_bot", pa.bool_()),
        pa.field("pinned", pa.bool_()),
        pa.field("mention_everyone", pa.bool_()),
        pa.field("tts", pa.bool_()),
        pa.field("flags", pa.int64()),
        pa.field("attachment_count", pa.int64()),
        pa.field("embed_count", pa.int64()),
        pa.field("mention_count", pa.int64()),
        pa.field("mention_role_count", pa.int64()),
        pa.field("sticker_count", pa.int64()),
        pa.field("reaction_count", pa.int64()),
        pa.field("referenced_message_id", pa.string()),
        pa.field("referenced_guild_id", pa.string()),
        pa.field("attachments_json", pa.string()),
        pa.field("embeds_json", pa.string()),
        pa.field("mentions_json", pa.string()),
        pa.field("mention_roles_json", pa.string()),
        pa.field("sticker_items_json", pa.string()),
        pa.field("reactions_json", pa.string()),
        pa.field("positive_score", pa.int64()),
        pa.field("matched_positive_terms", pa.string()),
    ]
)


def compile_channel_filters(
    include: list[str], exclude: list[str]
) -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    def compile_group(values: list[str], label: str) -> list[re.Pattern[str]]:
        patterns: list[re.Pattern[str]] = []
        for value in values:
            if not value.strip():
                continue
            try:
                patterns.append(re.compile(value.strip(), re.IGNORECASE))
            except re.error as error:
                raise ValueError(f"Invalid regex in {label}: {value!r} ({error})") from error
        return patterns

    return compile_group(include, "include"), compile_group(exclude, "exclude")


def is_channel_allowed(
    channel_name: str,
    include: list[re.Pattern[str]],
    exclude: list[re.Pattern[str]],
) -> bool:
    return (not include or any(item.search(channel_name) for item in include)) and not any(
        item.search(channel_name) for item in exclude
    )


def load_selected_servers(
    selected_servers_path: Path,
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    frame = pd.read_parquet(selected_servers_path)
    if frame.empty:
        raise ValueError("The selected servers file is empty.")

    if "is_selected" in frame.columns:
        def selected(value: Any) -> bool:
            if value is None or (not isinstance(value, str) and pd.isna(value)):
                return False
            if isinstance(value, str):
                return value.strip().casefold() in {"1", "true", "yes", "y"}
            return bool(value)

        frame = frame[frame["is_selected"].map(selected)].copy()
        if frame.empty:
            raise ValueError("No server has is_selected=true.")

    frame["guild_id"] = frame["guild_id"].astype(str)
    optional_columns = ["name", "positive_score", "matched_positive_terms"]
    for column in optional_columns:
        if column not in frame:
            frame[column] = None
    lookup = {
        row["guild_id"]: row
        for row in frame[["guild_id", *optional_columns]].to_dict(orient="records")
    }
    return lookup, set(lookup)


def ensure_new_output(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(
            "Output already exists. Choose another path to preserve the source and previous runs."
        )


def extract_member_guild_id(member_name: str) -> str | None:
    match = re.search(r"(\d+)\.json$", member_name)
    return match.group(1) if match else None


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def transform_message(
    message: dict[str, Any],
    guild_id: str,
    guild_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    author = message.get("author") or {}
    attachments = message.get("attachments") or []
    embeds = message.get("embeds") or []
    mentions = message.get("mentions") or []
    mention_roles = message.get("mention_roles") or []
    stickers = message.get("sticker_items") or []
    reactions = message.get("reactions") or []
    reference = message.get("message_reference") or {}
    thread = message.get("thread") or {}
    guild = guild_lookup[guild_id]
    content = message.get("content") or ""
    return {
        "guild_id": guild_id,
        "guild_name": _optional_string(guild.get("name")),
        "message_id": _optional_string(message.get("id")),
        "channel_id": _optional_string(message.get("channel_id")),
        "channel_name": _optional_string(message.get("channel_name")),
        "author_id": _optional_string(author.get("id")),
        "author_username": _optional_string(author.get("username")),
        "author_discriminator": _optional_string(author.get("discriminator")),
        "webhook_id": _optional_string(message.get("webhook_id")),
        "timestamp": _optional_string(message.get("timestamp")),
        "edited_timestamp": _optional_string(message.get("edited_timestamp")),
        "message_type": _optional_int(message.get("type")),
        "native_thread_id": _optional_string(message.get("thread_id") or thread.get("id")),
        "content": content,
        "content_length": len(content),
        "is_bot": bool(message.get("is_bot") or author.get("bot", False)),
        "pinned": bool(message.get("pinned")),
        "mention_everyone": bool(message.get("mention_everyone")),
        "tts": bool(message.get("tts")),
        "flags": _optional_int(message.get("flags")),
        "attachment_count": len(attachments),
        "embed_count": len(embeds),
        "mention_count": len(mentions),
        "mention_role_count": len(mention_roles),
        "sticker_count": len(stickers),
        "reaction_count": len(reactions),
        "referenced_message_id": _optional_string(reference.get("message_id")),
        "referenced_guild_id": _optional_string(reference.get("guild_id")),
        "attachments_json": _json(attachments),
        "embeds_json": _json(embeds),
        "mentions_json": _json(mentions),
        "mention_roles_json": _json(mention_roles),
        "sticker_items_json": _json(stickers),
        "reactions_json": _json(reactions),
        "positive_score": _optional_int(guild.get("positive_score")),
        "matched_positive_terms": _optional_string(guild.get("matched_positive_terms")),
    }


def extract_archive(
    archive: tarfile.TarFile,
    *,
    guild_lookup: dict[str, dict[str, Any]],
    output_path: Path,
    exclude_bots: bool,
    batch_size: int,
    include_channel_patterns: list[re.Pattern[str]],
    exclude_channel_patterns: list[re.Pattern[str]],
    on_server: Callable[[str], None] | None = None,
) -> dict[str, int]:
    selected_ids = set(guild_lookup)
    rows: list[dict[str, Any]] = []
    writer: pq.ParquetWriter | None = None
    stats = {"servers": 0, "messages": 0, "skipped_channels": 0, "invalid_json": 0}

    def flush() -> None:
        nonlocal writer
        if not rows:
            return
        table = pa.Table.from_pylist(rows, schema=MESSAGE_SCHEMA)
        if writer is None:
            writer = pq.ParquetWriter(output_path, MESSAGE_SCHEMA, compression="zstd")
        writer.write_table(table)
        rows.clear()

    try:
        for member in archive:
            guild_id = extract_member_guild_id(member.name) if member.isfile() else None
            if guild_id is None or guild_id not in selected_ids:
                continue
            source = archive.extractfile(member)
            if source is None:
                continue
            stats["servers"] += 1
            if on_server is not None:
                on_server(guild_id)
            for raw_line in source:
                if not raw_line.strip():
                    continue
                try:
                    message = json.loads(raw_line)
                except json.JSONDecodeError:
                    stats["invalid_json"] += 1
                    continue
                channel_name = str(message.get("channel_name") or "")
                if not is_channel_allowed(
                    channel_name, include_channel_patterns, exclude_channel_patterns
                ):
                    stats["skipped_channels"] += 1
                    continue
                row = transform_message(message, guild_id, guild_lookup)
                if exclude_bots and row["is_bot"]:
                    continue
                rows.append(row)
                stats["messages"] += 1
                if len(rows) >= batch_size:
                    flush()
        flush()
        if writer is None:
            raise ValueError("No messages were found in the selected scope.")
        return stats
    finally:
        if writer is not None:
            writer.close()
