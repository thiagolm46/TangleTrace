from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


MESSAGE_COLUMNS: tuple[str, ...] = (
    "message_id",
    "server_id",
    "channel_id",
    "author_id",
    "timestamp",
    "content",
    "native_reply_to",
    "mentions",
    "message_type",
    "reaction_count",
    "has_attachment",
    "is_bot",
    "guild_name",
    "channel_name",
    "edited_timestamp",
    "native_thread_id",
    "reactions",
    "attachments",
    "embeds",
    "mention_roles",
    "sticker_items",
    "is_webhook",
    "webhook_id",
    "pinned",
    "mention_everyone",
    "tts",
    "flags",
    "referenced_guild_id",
    "native_reply_evidence",
    "native_available_fields_json",
    "native_fields_json",
)

SAMPLE_MESSAGE_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "message_id",
    "is_context",
    "sequence",
)

ANNOTATION_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "source_message_id",
    "target_message_id",
    "annotator_id",
    "relation",
    "ambiguous",
    "confidence",
    "notes",
)

SOURCE_STATUS_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "source_message_id",
    "annotator_id",
    "source_status",
    "ambiguous",
    "confidence",
    "notes",
    "native_reply_to",
    "native_reply_evidence",
)

@dataclass(frozen=True, slots=True)
class AnnotationBundleArtifacts:
    messages_path: Path
    sample_messages_path: Path
    annotations_path: Path
    source_statuses_path: Path
    summary_path: Path


@dataclass(frozen=True, slots=True)
class PublishedAnnotationDatasetArtifacts:
    messages_path: Path
    sample_messages_path: Path
    annotations_path: Path
    source_statuses_path: Path
    silver_native_reply_edges_path: Path
    codebook_path: Path
    manifest_path: Path


def build_annotation_bundle(
    annotation_windows_path: Path,
    output_dir: Path,
) -> AnnotationBundleArtifacts:
    """Flatten annotation windows into stable message and human-label tables."""
    windows = pd.read_csv(annotation_windows_path, keep_default_na=False)
    _require_columns(windows, {"annotation_id", "messages_json"})
    messages_by_id: dict[str, dict[str, Any]] = {}
    sample_message_rows: list[dict[str, Any]] = []
    source_status_rows: list[dict[str, Any]] = []
    for window in windows.itertuples(index=False):
        sample_id = str(window.annotation_id)
        messages = _json_list(window.messages_json, "messages_json", sample_id)
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError(f"Invalid message in sample {sample_id}")
            message_id = _required_text(message, "message_id", sample_id)
            is_context = message.get("window_role") == "context"
            message_row = {
                    "message_id": message_id,
                    "server_id": _optional_text(message.get("server_id"))
                    or _optional_text(window.guild_id),
                    "channel_id": _optional_text(message.get("channel_id"))
                    or _optional_text(window.channel_id),
                    "author_id": _optional_text(message.get("author_id")),
                    "timestamp": _optional_text(message.get("timestamp")),
                    "content": str(message.get("content") or ""),
                    "native_reply_to": _optional_text(
                        message.get("native_reply_to_message_id")
                    ),
                    "mentions": _json_text(message.get("mentions", [])),
                    "message_type": _optional_text(message.get("message_type")),
                    "reaction_count": len(message.get("reactions") or []),
                    "has_attachment": bool(message.get("attachments") or []),
                    "is_bot": bool(message.get("is_bot")),
                    "guild_name": _optional_text(message.get("guild_name"))
                    or _optional_text(window.guild_name),
                    "channel_name": _optional_text(message.get("channel_name"))
                    or _optional_text(window.channel_name),
                    "edited_timestamp": _optional_text(message.get("edited_timestamp")),
                    "native_thread_id": _optional_text(message.get("native_thread_id")),
                    "reactions": _json_text(message.get("reactions", [])),
                    "attachments": _json_text(message.get("attachments", [])),
                    "embeds": _json_text(message.get("embeds", [])),
                    "mention_roles": _json_text(message.get("mention_roles", [])),
                    "sticker_items": _json_text(message.get("sticker_items", [])),
                    "is_webhook": bool(message.get("is_webhook")),
                    "webhook_id": _optional_text(message.get("webhook_id")),
                    "pinned": bool(message.get("pinned")),
                    "mention_everyone": bool(message.get("mention_everyone")),
                    "tts": bool(message.get("tts")),
                    "flags": _optional_int(message.get("flags")),
                    "referenced_guild_id": _optional_text(
                        message.get("referenced_guild_id")
                    ),
                    "native_reply_evidence": _optional_text(
                        message.get("native_reply_evidence")
                    ),
                    "native_available_fields_json": _json_text(
                        message.get("native_available_fields", [])
                    ),
                    "native_fields_json": _json_text(
                        _parse_native_fields(message.get("native_fields_json"), sample_id)
                    ),
                }
            previous = messages_by_id.setdefault(message_id, message_row)
            if previous != message_row:
                raise ValueError(f"Inconsistent metadata for message_id: {message_id}")
            sample_message_rows.append(
                {
                    "sample_id": sample_id,
                    "message_id": message_id,
                    "is_context": is_context,
                    "sequence": int(message.get("sequence", 0)),
                }
            )
            if not is_context:
                source_status_rows.append(
                    {
                        "sample_id": sample_id,
                        "source_message_id": message_id,
                        "annotator_id": "",
                        "source_status": "pending",
                        "ambiguous": False,
                        "confidence": "",
                        "notes": "",
                        "native_reply_to": _optional_text(
                            message.get("native_reply_to_message_id")
                        ),
                        "native_reply_evidence": _optional_text(
                            message.get("native_reply_evidence")
                        ),
                    }
                )

    messages = pd.DataFrame.from_records(
        list(messages_by_id.values()),
        columns=MESSAGE_COLUMNS,
    )
    sample_messages = pd.DataFrame.from_records(
        sample_message_rows,
        columns=SAMPLE_MESSAGE_COLUMNS,
    )
    annotations = _empty_annotations()
    source_statuses = pd.DataFrame.from_records(
        source_status_rows,
        columns=SOURCE_STATUS_COLUMNS,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    messages_path = output_dir / "messages.parquet"
    sample_messages_path = output_dir / "sample_messages.parquet"
    annotations_path = output_dir / "annotations.parquet"
    source_statuses_path = output_dir / "source_statuses.parquet"
    summary_path = output_dir / "annotation_bundle_summary.json"
    messages.to_parquet(messages_path, index=False)
    sample_messages.to_parquet(sample_messages_path, index=False)
    annotations.to_parquet(annotations_path, index=False)
    source_statuses.to_parquet(source_statuses_path, index=False)
    summary_path.write_text(
        json.dumps(
            {
                "annotation_windows_path": str(annotation_windows_path),
                "message_table_unit": "canonical_message",
                "sample_message_table_unit": "sample_message_membership",
                "annotation_table_unit": "directed_reply_edge",
                "source_status_table_unit": "annotated_message_decision",
                "sample_count": int(windows["annotation_id"].nunique()),
                "unique_message_count": int(len(messages)),
                "message_membership_count": int(len(sample_messages)),
                "context_membership_count": int(sample_messages["is_context"].sum()),
                "annotated_message_count": int((~sample_messages["is_context"]).sum()),
                "annotation_rows_initial": 0,
                "source_status_rows_initial": int(len(source_statuses)),
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return AnnotationBundleArtifacts(
        messages_path=messages_path,
        sample_messages_path=sample_messages_path,
        annotations_path=annotations_path,
        source_statuses_path=source_statuses_path,
        summary_path=summary_path,
    )


def publish_annotation_dataset(
    bundle_dir: Path,
    native_reply_edges_path: Path,
    codebook_path: Path,
    output_dir: Path,
) -> PublishedAnnotationDatasetArtifacts:
    """Publish the minimal, self-contained files needed for human annotation."""
    source_paths = {
        "messages.parquet": bundle_dir / "messages.parquet",
        "sample_messages.parquet": bundle_dir / "sample_messages.parquet",
        "annotations.parquet": bundle_dir / "annotations.parquet",
        "source_statuses.parquet": bundle_dir / "source_statuses.parquet",
        "silver_native_reply_edges.parquet": native_reply_edges_path,
        "CODEBOOK.md": codebook_path,
    }
    missing = [name for name, path in source_paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Artefatos necessarios ausentes: " + ", ".join(sorted(missing))
        )
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Diretorio de publicacao ja existe: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    published_paths = {
        name: output_dir / name
        for name in source_paths
    }
    for name, source_path in source_paths.items():
        shutil.copy2(source_path, published_paths[name])

    messages = pd.read_parquet(published_paths["messages.parquet"])
    sample_messages = pd.read_parquet(published_paths["sample_messages.parquet"])
    annotations = pd.read_parquet(published_paths["annotations.parquet"])
    source_statuses = pd.read_parquet(published_paths["source_statuses.parquet"])
    silver_edges = pd.read_parquet(published_paths["silver_native_reply_edges.parquet"])
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": output_dir.name,
                "annotation_unit": "directed_reply_edge",
                "message_table_unit": "canonical_message",
                "sample_message_table_unit": "sample_message_membership",
                "conversation_id_rule": "not_materialized_in_preparation_pipeline",
                "native_reply_semantics": "positive_observed_or_unknown_never_negative",
                "files": {
                    name: {
                        "sha256": _sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                    for name, path in published_paths.items()
                },
                "counts": {
                    "sample_count": int(sample_messages["sample_id"].nunique()),
                    "message_membership_count": int(len(sample_messages)),
                    "unique_message_count": int(len(messages)),
                    "context_membership_count": int(sample_messages["is_context"].sum()),
                    "annotated_message_count": int((~sample_messages["is_context"]).sum()),
                    "human_annotation_edge_count": int(len(annotations)),
                    "source_status_count": int(len(source_statuses)),
                    "silver_native_reply_edge_count": int(len(silver_edges)),
                },
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return PublishedAnnotationDatasetArtifacts(
        messages_path=published_paths["messages.parquet"],
        sample_messages_path=published_paths["sample_messages.parquet"],
        annotations_path=published_paths["annotations.parquet"],
        source_statuses_path=published_paths["source_statuses.parquet"],
        silver_native_reply_edges_path=published_paths[
            "silver_native_reply_edges.parquet"
        ],
        codebook_path=published_paths["CODEBOOK.md"],
        manifest_path=manifest_path,
    )


def _empty_annotations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sample_id": pd.Series(dtype="string"),
            "source_message_id": pd.Series(dtype="string"),
            "target_message_id": pd.Series(dtype="string"),
            "annotator_id": pd.Series(dtype="string"),
            "relation": pd.Series(dtype="string"),
            "ambiguous": pd.Series(dtype="bool"),
            "confidence": pd.Series(dtype="string"),
            "notes": pd.Series(dtype="string"),
        }
    )


def _require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError("Window is missing required columns: " + ", ".join(sorted(missing)))


def _json_list(value: Any, column: str, sample_id: str) -> list[Any]:
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {column} of sample {sample_id}") from error
    if not isinstance(parsed, list):
        raise ValueError(f"{column} must contain a list in sample {sample_id}")
    return parsed


def _parse_native_fields(value: Any, sample_id: str) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid native_fields_json in sample {sample_id}") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"native_fields_json must contain an object in sample {sample_id}")
    return parsed


def _required_text(record: dict[str, Any], field: str, sample_id: str) -> str:
    value = _optional_text(record.get(field))
    if value is None:
        raise ValueError(f"Message is missing {field} in sample {sample_id}")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()