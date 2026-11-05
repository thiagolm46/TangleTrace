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

MATERIALIZED_EDGE_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "source_message_id",
    "target_message_id",
    "annotator_id",
    "relation",
    "ambiguous",
    "confidence",
    "notes",
    "edge_origin",
)

COMPONENT_COLUMNS: tuple[str, ...] = (
    "conversation_id",
    "message_id",
    "server_id",
    "channel_id",
    "component_message_count",
)

VALID_SOURCE_STATUSES = frozenset(
    {
        "pending",
        "complete",
        "no_reply",
        "outside_context",
        "ambiguous",
        "new_conversation",
    }
)

VALID_CONFIDENCE = frozenset({"high", "medium", "low"})


@dataclass(frozen=True, slots=True)
class AnnotationBundleArtifacts:
    messages_path: Path
    sample_messages_path: Path
    annotations_path: Path
    source_statuses_path: Path
    summary_path: Path


@dataclass(frozen=True, slots=True)
class MaterializedAnnotationArtifacts:
    edges_path: Path
    components_path: Path
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


def materialize_annotation_tables(
    messages_path: Path,
    sample_messages_path: Path,
    annotations_path: Path,
    source_statuses_path: Path,
    output_dir: Path,
    *,
    include_ambiguous: bool = False,
) -> MaterializedAnnotationArtifacts:
    """Validate flat human labels and derive components from accepted reply edges."""
    messages = pd.read_parquet(messages_path)
    sample_messages = pd.read_parquet(sample_messages_path)
    annotations = pd.read_parquet(annotations_path)
    source_statuses = pd.read_parquet(source_statuses_path)
    _require_columns(
        messages,
        {"message_id", "server_id", "channel_id"},
    )
    _require_columns(sample_messages, set(SAMPLE_MESSAGE_COLUMNS))
    _require_columns(annotations, set(ANNOTATION_COLUMNS))
    _require_columns(source_statuses, set(SOURCE_STATUS_COLUMNS))

    message_by_sample = _index_sample_messages(messages, sample_messages)
    source_status_by_key = _index_source_statuses(source_statuses, message_by_sample)
    materialized_edges = _validate_annotations(
        annotations,
        message_by_sample=message_by_sample,
        source_status_by_key=source_status_by_key,
        include_ambiguous=include_ambiguous,
    )
    materialized_edges.extend(
        _new_conversation_self_links(source_statuses, message_by_sample)
    )
    edges = pd.DataFrame.from_records(materialized_edges, columns=MATERIALIZED_EDGE_COLUMNS)
    components = _build_components(edges, message_by_sample)

    output_dir.mkdir(parents=True, exist_ok=True)
    edges_path = output_dir / "human_reply_edges.parquet"
    components_path = output_dir / "human_reply_components.parquet"
    summary_path = output_dir / "human_annotation_summary.json"
    edges.to_parquet(edges_path, index=False)
    components.to_parquet(components_path, index=False)
    summary_path.write_text(
        json.dumps(
            {
                "messages_path": str(messages_path),
                "sample_messages_path": str(sample_messages_path),
                "annotations_path": str(annotations_path),
                "source_statuses_path": str(source_statuses_path),
                "annotation_unit": "directed_reply_edge",
                "conversation_id_rule": "undirected_connected_components_of_accepted_human_edges",
                "include_ambiguous": include_ambiguous,
                "reply_edges_submitted": int((annotations["relation"] == "reply").sum()),
                "reply_edges_materialized": int((edges["relation"] == "reply").sum()),
                "new_conversation_self_links": int(
                    (edges["edge_origin"] == "derived_new_conversation").sum()
                ),
                "human_conversation_count": int(components["conversation_id"].nunique()),
                "human_component_message_count": int(len(components)),
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return MaterializedAnnotationArtifacts(
        edges_path=edges_path,
        components_path=components_path,
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
                "conversation_id_rule": "derived_after_annotation_from_connected_components",
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


def _index_sample_messages(
    messages: pd.DataFrame,
    sample_messages: pd.DataFrame,
) -> dict[tuple[str, str], dict[str, Any]]:
    canonical_by_id: dict[str, dict[str, Any]] = {}
    for message in messages.to_dict(orient="records"):
        message_id = _required_text(message, "message_id", "messages")
        if message_id in canonical_by_id:
            raise ValueError(f"Duplicate message_id in messages.parquet: {message_id}")
        canonical_by_id[message_id] = message
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for membership in sample_messages.to_dict(orient="records"):
        sample_id = _required_text(membership, "sample_id", "sample_messages")
        message_id = _required_text(membership, "message_id", sample_id)
        key = (sample_id, message_id)
        if key in indexed:
            raise ValueError(f"Duplicate message in sample {sample_id}: {message_id}")
        message = canonical_by_id.get(message_id)
        if message is None:
            raise ValueError(f"Participation has no canonical message: {message_id}")
        indexed[key] = {**message, **membership}
    return indexed


def _index_source_statuses(
    source_statuses: pd.DataFrame,
    message_by_sample: dict[tuple[str, str], dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for status in source_statuses.to_dict(orient="records"):
        sample_id = _required_text(status, "sample_id", "source_statuses")
        source_id = _required_text(status, "source_message_id", sample_id)
        source_status = _required_text(status, "source_status", sample_id)
        key = (sample_id, source_id)
        source = message_by_sample.get(key)
        if source is None or bool(source["is_context"]):
            raise ValueError(f"Status source is outside the annotated segment: {source_id}")
        if source_status not in VALID_SOURCE_STATUSES:
            raise ValueError(f"Invalid source status in {sample_id}: {source_status}")
        if key in indexed:
            raise ValueError(f"Duplicate status in {sample_id}: {source_id}")
        indexed[key] = status
    return indexed


def _validate_annotations(
    annotations: pd.DataFrame,
    *,
    message_by_sample: dict[tuple[str, str], dict[str, Any]],
    source_status_by_key: dict[tuple[str, str], dict[str, Any]],
    include_ambiguous: bool,
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for annotation in annotations.to_dict(orient="records"):
        sample_id = _required_text(annotation, "sample_id", "annotations")
        source_id = _required_text(annotation, "source_message_id", sample_id)
        target_id = _required_text(annotation, "target_message_id", sample_id)
        annotator_id = _required_text(annotation, "annotator_id", sample_id)
        relation = _required_text(annotation, "relation", sample_id)
        confidence = _required_text(annotation, "confidence", sample_id)
        ambiguous = _as_bool(annotation.get("ambiguous"), "ambiguous", sample_id)
        if relation != "reply":
            raise ValueError(f"Invalid human relation in {sample_id}: {relation}")
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"Invalid human confidence in {sample_id}: {confidence}")
        source_key = (sample_id, source_id)
        source = message_by_sample.get(source_key)
        target = message_by_sample.get((sample_id, target_id))
        if source is None or bool(source["is_context"]):
            raise ValueError(f"Edge source is outside the annotated segment: {source_id}")
        if target is None:
            raise ValueError(f"Edge target is outside the sample: {target_id}")
        status = source_status_by_key.get(source_key)
        if status is None or status["source_status"] != "complete":
            raise ValueError(f"Human edge requires a complete source: {source_id}")
        if int(target["sequence"]) >= int(source["sequence"]):
            raise ValueError(f"Antecedent is not strictly earlier: {source_id} -> {target_id}")
        if ambiguous and not include_ambiguous:
            continue
        materialized.append(
            {
                "sample_id": sample_id,
                "source_message_id": source_id,
                "target_message_id": target_id,
                "annotator_id": annotator_id,
                "relation": relation,
                "ambiguous": ambiguous,
                "confidence": confidence,
                "notes": str(annotation.get("notes") or ""),
                "edge_origin": "human_reply",
            }
        )
    return materialized


def _new_conversation_self_links(
    source_statuses: pd.DataFrame,
    message_by_sample: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for status in source_statuses.to_dict(orient="records"):
        if status["source_status"] != "new_conversation":
            continue
        sample_id = str(status["sample_id"])
        source_id = str(status["source_message_id"])
        if (sample_id, source_id) not in message_by_sample:
            raise ValueError(f"New conversation has no visible source: {source_id}")
        rows.append(
            {
                "sample_id": sample_id,
                "source_message_id": source_id,
                "target_message_id": source_id,
                "annotator_id": _optional_text(status.get("annotator_id")) or "",
                "relation": "new_conversation",
                "ambiguous": _as_bool(status.get("ambiguous"), "ambiguous", sample_id),
                "confidence": _optional_text(status.get("confidence")) or "",
                "notes": str(status.get("notes") or ""),
                "edge_origin": "derived_new_conversation",
            }
        )
    return rows


def _build_components(
    edges: pd.DataFrame,
    message_by_sample: dict[tuple[str, str], dict[str, Any]],
) -> pd.DataFrame:
    if edges.empty:
        return pd.DataFrame(columns=COMPONENT_COLUMNS)
    graph = _UnionFind()
    metadata_by_message: dict[str, tuple[str | None, str | None]] = {}
    for edge in edges.itertuples(index=False):
        sample_id = str(edge.sample_id)
        source_id = str(edge.source_message_id)
        target_id = str(edge.target_message_id)
        source = message_by_sample[(sample_id, source_id)]
        target = message_by_sample[(sample_id, target_id)]
        source_metadata = (source["server_id"], source["channel_id"])
        target_metadata = (target["server_id"], target["channel_id"])
        if source_metadata != target_metadata:
            raise ValueError(f"Human edge crosses channels: {source_id} -> {target_id}")
        for message_id in (source_id, target_id):
            previous = metadata_by_message.setdefault(message_id, source_metadata)
            if previous != source_metadata:
                raise ValueError(f"Human message appears in different channels: {message_id}")
        graph.union(source_id, target_id)
    members_by_root: dict[str, list[str]] = {}
    for message_id in metadata_by_message:
        members_by_root.setdefault(graph.find(message_id), []).append(message_id)
    rows: list[dict[str, Any]] = []
    for members in members_by_root.values():
        ordered_members = sorted(members)
        server_id, channel_id = metadata_by_message[ordered_members[0]]
        conversation_id = _conversation_id(str(channel_id or ""), ordered_members)
        for message_id in ordered_members:
            rows.append(
                {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "server_id": server_id,
                    "channel_id": channel_id,
                    "component_message_count": len(ordered_members),
                }
            )
    return pd.DataFrame.from_records(rows, columns=COMPONENT_COLUMNS)


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _conversation_id(channel_id: str, message_ids: list[str]) -> str:
    identifier = (channel_id + "\0" + "\0".join(message_ids)).encode("utf-8")
    return f"HUMAN_{hashlib.sha1(identifier).hexdigest()[:12]}"


def _require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError("Window is missing required columns: " + ", ".join(sorted(missing)))


def _json_list(value: Any, column: str, sample_id: str) -> list[Any]:
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {column} for sample {sample_id}") from error
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


def _as_bool(value: Any, field: str, sample_id: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().casefold() in {"true", "false"}:
        return value.strip().casefold() == "true"
    raise ValueError(f"{field} must be a boolean in sample {sample_id}")


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()