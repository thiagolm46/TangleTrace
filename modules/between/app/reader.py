"""Transactional, batched import that does not modify sampled source files."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import duckdb

from .domain import Invalid, canonical, signature
from .storage import now, pack

csv.field_size_limit(128 * 1024 * 1024)
MEMBERSHIP_FIELDS = {"annotation_id", "position", "is_context", "target_inclusion_probability", "target_design_weight"}
JSON_FIELDS = ("attachments", "embeds", "mentions", "mention_roles", "sticker_items", "reactions")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_value(value, field):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise Invalid(f"{field} must be a boolean.")


def iso_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.isoformat()
    except (ValueError, TypeError):
        raise Invalid("Timestamp is missing, invalid, or has no time zone.")


def from_parquet(record, sequence):
    raw = {k: v for k, v in record.items() if k not in MEMBERSHIP_FIELDS}
    target = raw.get("referenced_message_id") if raw.get("message_type") == 19 else None
    context = bool_value(record["is_context"], "is_context")
    item = {**raw, "sequence": sequence, "window_role": "context" if context else "annotated",
            "requires_reply_annotation": not context, "server_id": str(raw["guild_id"]),
            "timestamp": iso_timestamp(raw.get("timestamp")),
            "native_reply_to_message_id": str(target).strip() if target else None,
            "native_reply_evidence": "positive_observed" if target else "unknown",
            "native_available_fields": sorted(raw), "native_fields_json": canonical(raw),
            "target_inclusion_probability": record.get("target_inclusion_probability"),
            "target_design_weight": record.get("target_design_weight"),
            "sampling_position": record["position"]}
    for field in JSON_FIELDS:
        item[field] = json.loads(raw.get(field + "_json") or "[]")
    return item


def validate_window(meta, messages):
    sample_id = str(meta.get("annotation_id", "")).strip()
    if not sample_id or (meta.get("window_id") and meta["window_id"] != sample_id):
        raise Invalid("annotation_id and window_id are missing or do not match.")
    if not messages:
        raise Invalid(f"Empty window: {sample_id}")
    seen, sequences, targets, previous_time = set(), set(), 0, None
    for m in messages:
        for field in ("message_id", "channel_id", "guild_id", "author_id"):
            if not isinstance(m.get(field), str) or not m[field].strip():
                raise Invalid(f"{field} is missing or invalid in window {sample_id}.")
        if m["message_id"] in seen:
            raise Invalid(f"Duplicate message in window {sample_id}.")
        seen.add(m["message_id"])
        seq = m.get("sequence")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1 or seq in sequences:
            raise Invalid(f"Invalid or duplicate sequence in window {sample_id}.")
        sequences.add(seq)
        role = m.get("window_role")
        if role not in {"annotated", "context"}:
            raise Invalid(f"Invalid role in window {sample_id}.")
        required = bool_value(m.get("requires_reply_annotation"), "requires_reply_annotation")
        if required != (role == "annotated"):
            raise Invalid(f"Role and requires_reply_annotation disagree in window {sample_id}.")
        m["requires_reply_annotation"] = required
        if str(meta.get("channel_id")) != m["channel_id"] or str(meta.get("guild_id")) != m["guild_id"]:
            raise Invalid(f"Server/channel mismatch in window {sample_id}.")
        m["timestamp"] = iso_timestamp(m.get("timestamp"))
        timestamp = datetime.fromisoformat(m["timestamp"])
        if previous_time and timestamp < previous_time:
            raise Invalid(f"Inconsistent temporal order in window {sample_id}.")
        previous_time = timestamp
        if not required and (m.get("target_inclusion_probability") is not None or m.get("target_design_weight") is not None):
            raise Invalid(f"Context message has a target probability/weight in window {sample_id}.")
        targets += required
        for field in JSON_FIELDS:
            if field in m and m[field] is not None and not isinstance(m[field], list):
                raise Invalid(f"Invalid {field} metadata in window {sample_id}.")
    if int(meta.get("annotated_message_count", targets)) != targets:
        raise Invalid(f"Target count mismatch in window {sample_id}.")
    target_messages = [m for m in messages if m["requires_reply_annotation"]]
    for field, index in (("first_annotated_message_id", 0), ("last_annotated_message_id", -1)):
        if meta.get(field) and (not target_messages or meta[field] != target_messages[index]["message_id"]):
            raise Invalid(f"{field} boundary mismatch in window {sample_id}.")
    if meta.get("context_message_count") not in (None, "") and int(meta["context_message_count"]) != len(messages) - targets:
        raise Invalid(f"Context count mismatch in window {sample_id}.")
    if meta.get("total_message_count") not in (None, "") and int(meta["total_message_count"]) != len(messages):
        raise Invalid(f"Total count mismatch in window {sample_id}.")
    meta.update({"window_id": sample_id, "sample_id": sample_id,
                 "guild_name": meta.get("guild_name") or messages[0].get("guild_name") or meta["guild_id"],
                 "channel_name": meta.get("channel_name") or messages[0].get("channel_name") or meta["channel_id"],
                 "annotated_message_count": targets, "context_message_count": len(messages) - targets,
                 "total_message_count": len(messages)})
    return meta, messages


class SamplingRunReader:
    def __init__(self, store):
        self.store = store

    def import_run(self, source, progress=lambda *args: None):
        source = Path(source).expanduser().resolve()
        if source.suffix.lower() == ".parquet":
            if source.name != "sampled_messages.parquet" or not source.is_file():
                raise Invalid("Select sampled_messages.parquet together with selected_windows.csv, or select the sampling folder.")
            source = source.parent
        directory = source if source.is_dir() else source.parent
        pair = source.is_dir() and all((source / n).is_file() for n in ("sampled_messages.parquet", "selected_windows.csv"))
        csv_path = directory / "annotation_windows.csv" if source.is_dir() else source
        if not pair and not csv_path.is_file():
            raise Invalid("Select the folder containing sampled_messages.parquet and selected_windows.csv, or select annotation_windows.csv.")
        manifest_path = directory / "manifest.json"
        diagnostics, hashes = [], {}
        manifest = None
        progress("Checking files and hashes…", 0)
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            for name, expected in manifest.get("outputs", {}).items():
                path = (directory / name).resolve()
                if not path.is_relative_to(directory):
                    raise Invalid("External path in integrity manifest.")
                if path.is_file():
                    actual = sha256_file(path)
                    if actual != expected:
                        raise Invalid(f"SHA-256 mismatch: {name}. The source file has changed.")
                    hashes[name] = actual
                else:
                    diagnostics.append(f"Auxiliary artifact missing: {name}")
            hashes["manifest.json"] = sha256_file(manifest_path)
        else:
            diagnostics.append("No source manifest; identity was computed from the supplied files.")
        names = ["sampled_messages.parquet", "selected_windows.csv"] if pair else [csv_path.name]
        for name in names:
            hashes.setdefault(name, sha256_file(directory / name))
        # With a validated manifest, both supported input formats reuse the same import_id.
        verified_manifest = manifest and all(name in manifest.get("outputs", {}) for name in names)
        import_id = signature({"manifest": hashes["manifest.json"]}) if verified_manifest else signature(hashes)
        with self.store.connect() as db:
            existing = db.execute("SELECT id FROM imports WHERE id=?", (import_id,)).fetchone()
            if existing:
                return {"import_id": import_id, "reused": True, "diagnostics": diagnostics}
            provenance = {"source_manifest_hash": hashes.get("manifest.json"), "hashes": hashes,
                          "route": "parquet" if pair else "csv", "diagnostics": diagnostics,
                          "manifest": manifest, "adapter_version": "0.1.0"}
            db.execute("INSERT INTO imports VALUES(?,?,?,?,?)", (import_id, directory.name, str(source), now(), canonical(provenance)))
            count, targets, contexts = 0, 0, 0
            canonical_messages = {}
            iterator = self._parquet(directory) if pair else self._csv(csv_path, diagnostics)
            for meta, messages in iterator:
                meta, messages = validate_window(meta, messages)
                for m in messages:
                    # Check canonical identity without mixing window participations.
                    native = m.get("native_fields_json")
                    raw = json.loads(native) if native else {k: v for k, v in m.items() if k not in MEMBERSHIP_FIELDS and k not in {"sequence", "window_role", "requires_reply_annotation", "sampling_position"}}
                    sig = signature(raw)
                    previous = canonical_messages.setdefault(m["message_id"], sig)
                    if previous != sig:
                        raise Invalid(f"Inconsistent canonical metadata: {m['message_id']}.")
                target_count = meta["annotated_message_count"]
                context_count = meta["context_message_count"]
                db.execute("INSERT INTO windows VALUES(?,?,?,?,?,?,?)", (import_id, meta["sample_id"], canonical(meta), pack(messages), signature(messages), target_count, context_count))
                count += 1
                targets += target_count
                contexts += context_count
                progress(f"Indexing windows: {count} · {targets:,} targets", count)
            if not count:
                raise Invalid("No windows found.")
            if manifest and manifest.get("counts"):
                actual = {"selected_windows": count, "target_messages": targets, "context_memberships": contexts}
                for key, value in actual.items():
                    if key in manifest["counts"] and manifest["counts"][key] != value:
                        raise Invalid(f"Count for {key} does not match the manifest.")
            provenance.update({"window_count": count, "target_count": targets, "context_count": contexts})
            db.execute("UPDATE imports SET provenance=? WHERE id=?", (canonical(provenance), import_id))
        return {"import_id": import_id, "reused": False, "diagnostics": diagnostics,
                "window_count": count, "target_count": targets}

    def _parquet(self, directory):
        with (directory / "selected_windows.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        metas = {}
        for row in rows:
            key = row.get("annotation_id")
            if not key or key in metas:
                raise Invalid("Missing or duplicate window ID in selected_windows.csv.")
            metas[key] = row
        db = duckdb.connect()
        try:
            db.execute("SET memory_limit='512MB'")
            db.execute("SET threads=2")
            db.execute("SET enable_progress_bar=false")
            result = db.execute("SELECT * FROM read_parquet(?) ORDER BY annotation_id,position", [str(directory / "sampled_messages.parquet")])
            current, messages, seen, positions = None, [], set(), set()
            for batch in result.fetch_record_batch(512):
                for row in batch.to_pylist():
                    key = row["annotation_id"]
                    if key != current:
                        if current is not None:
                            seen.add(current)
                            yield metas[current], messages
                        if key not in metas:
                            raise Invalid("Participation refers to a window missing from selected_windows.csv.")
                        current, messages, positions = key, [], set()
                    position = row["position"]
                    if not isinstance(position, int) or position < 1 or position in positions:
                        raise Invalid(f"Invalid or duplicate position in window {key}.")
                    positions.add(position)
                    messages.append(from_parquet(row, len(messages) + 1))
            if current is not None:
                seen.add(current)
                yield metas[current], messages
            if seen != metas.keys():
                raise Invalid("Selected windows have no participations in the Parquet file.")
        finally:
            db.close()

    def _csv(self, path, diagnostics):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                messages = json.loads(row.pop("messages_json"))
                for field in ("human_reply_edges_json", "human_reply_source_statuses_json"):
                    value = json.loads(row.pop(field, "[]") or "[]")
                    if value:
                        diagnostics.append(f"{row.get('annotation_id')}: source human data remain in the source and were not imported as decisions in this session.")
                if not isinstance(messages, list):
                    raise Invalid("messages_json must contain a list.")
                messages.sort(key=lambda m: m["sequence"])
                yield row, messages
