"""Reconstruct the server review queue and apply explicit human decisions."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .storage import read_records, sha256_file, write_records_with_manifest


def _indexed_records(path: Path) -> dict[str, dict[str, Any]]:
    records = read_records(path)
    if not records:
        raise ValueError(f"server table is empty: {path}")
    indexed = {}
    for record in records:
        guild_id = record.get("guild_id")
        if not isinstance(guild_id, str) or not guild_id.strip() or guild_id != guild_id.strip():
            raise ValueError(f"guild_id must be a nonblank canonical string: {path}")
        if guild_id in indexed:
            raise ValueError(f"duplicate guild_id {guild_id}: {path}")
        indexed[guild_id] = record
    return indexed


def prioritize_servers(input_path: Path, output_path: Path) -> tuple[Path, Path]:
    records = _indexed_records(input_path)
    scores = []
    for record in records.values():
        value = record.get("software_affinity_score")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("software_affinity_score must contain finite numeric values")
        scores.append(float(value))
    positive = pd.Series([score for score in scores if score > 0], dtype=float)
    if positive.empty:
        raise ValueError("cannot calculate Tukey's upper fence without positive affinity scores")
    q1, q3 = positive.quantile([0.25, 0.75], interpolation="linear")
    upper_fence = float(q3 + 1.5 * (q3 - q1))
    candidates = [
        record for record, score in zip(records.values(), scores)
        if score > upper_fence
    ]
    candidates.sort(key=lambda item: (-item["software_affinity_score"], item["guild_id"]))
    if not candidates:
        raise ValueError("no servers exceed the positive-score Tukey upper fence")
    manifest = {
        "manifest_schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "prioritize-servers",
        "inputs": [{"path": str(input_path.resolve()), "sha256": sha256_file(input_path), "immutable_source": True}],
        "implementation_sha256": sha256_file(Path(__file__)),
        "parameters": {"positive_only": True, "interpolation": "linear", "iqr_multiplier": 1.5, "comparison": "strictly_greater"},
        "statistics": {"q1": float(q1), "q3": float(q3), "upper_fence": upper_fence},
        "counts": {"evaluated_servers": len(records), "positive_servers": len(positive), "candidate_servers": len(candidates)},
        "source_data_policy": "read_only_immutable",
    }
    return write_records_with_manifest(candidates, output_path, manifest)


def apply_server_review(
    input_path: Path, review_path: Path, output_path: Path,
) -> tuple[Path, Path]:
    candidates = _indexed_records(input_path)
    review = _indexed_records(review_path)
    if candidates.keys() != review.keys():
        missing = sorted(candidates.keys() - review.keys())
        extra = sorted(review.keys() - candidates.keys())
        raise ValueError(f"review must cover exactly the candidate IDs; missing={missing}, extra={extra}")
    selected = []
    for guild_id, decision in review.items():
        if decision.get("decision") not in {"accept", "reject"}:
            raise ValueError(f"invalid decision for {guild_id}; expected accept or reject")
        if decision["decision"] == "accept":
            selected.append({
                **candidates[guild_id],
                "is_selected": True,
                "manual_decision": "accept",
            })
    if not selected:
        raise ValueError("review accepts no servers; extraction requires a nonempty selection")
    selected.sort(key=lambda item: item["guild_id"])
    manifest = {
        "manifest_schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "apply-server-review",
        "inputs": [{"path": str(path.resolve()), "sha256": sha256_file(path), "immutable_source": True} for path in (input_path, review_path)],
        "implementation_sha256": sha256_file(Path(__file__)),
        "counts": {"candidate_servers": len(candidates), "selected_servers": len(selected), "rejected_servers": len(review) - len(selected)},
        "limitations": ["recorded decisions reproduce a historical review, not independent human agreement; per-server rationales were not preserved"],
        "source_data_policy": "read_only_immutable",
    }
    return write_records_with_manifest(selected, output_path, manifest)
