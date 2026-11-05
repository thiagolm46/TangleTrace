from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OutputExistsError(FileExistsError):
    """Raised when a command would replace an artifact without explicit consent."""


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path_for(output_path: str | Path) -> Path:
    output = Path(output_path)
    return output.with_name(f"{output.name}.manifest.json")


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (datetime, Path)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _reserve_temp(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    os.close(descriptor)
    return Path(raw_path)


def _commit_complete_file(temp_path: Path, target: Path, *, overwrite: bool) -> None:
    """Expose a complete file atomically, refusing replacement by default."""

    if overwrite:
        os.replace(temp_path, target)
        return
    try:
        # The temporary file and target share a directory/filesystem. Creating a
        # hard link is atomic and fails if target already exists; unlinking the
        # private name then leaves the completed artifact in place.
        os.link(temp_path, target)
    except FileExistsError as error:
        raise OutputExistsError(
            f"output already exists: {target}; pass --overwrite to replace it"
        ) from error
    else:
        temp_path.unlink()


def atomic_write_bytes(path: str | Path, payload: bytes, *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise OutputExistsError(
            f"output already exists: {target}; pass --overwrite to replace it"
        )
    temp_path = _reserve_temp(target)
    try:
        with temp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _commit_complete_file(temp_path, target, overwrite=overwrite)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_records_temp(records: Sequence[Mapping[str, Any]], temp_path: Path, suffix: str) -> None:
    normalized = [dict(record) for record in records]
    if suffix in {".json", ".txt"}:
        payload = json.dumps(
            normalized,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ).encode("utf-8") + b"\n"
        with temp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return
    if suffix in {".jsonl", ".ndjson"}:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in normalized:
                handle.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=_json_default,
                    )
                )
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return
    if suffix == ".csv":
        fieldnames = list(normalized[0]) if normalized else []
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
            if fieldnames:
                writer.writeheader()
                writer.writerows(normalized)
            handle.flush()
            os.fsync(handle.fileno())
        return
    if suffix == ".parquet":
        try:
            import pandas as pd
        except ImportError as error:  # pragma: no cover - project dependency guard
            raise RuntimeError("writing Parquet requires the project's pandas/pyarrow dependencies") from error
        pd.DataFrame(normalized).to_parquet(temp_path, index=False)
        # Windows requires a writable descriptor for fsync().  The Parquet
        # writer has already closed the file; reopen it without truncation so
        # the completed temporary artifact is durable before publication.
        with temp_path.open("r+b") as handle:
            os.fsync(handle.fileno())
        return
    raise ValueError(f"unsupported output format '{suffix}' (use .json, .jsonl, .csv, or .parquet)")


def write_records_with_manifest(
    records: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    manifest: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Write an artifact and its provenance manifest with overwrite protection."""

    output = Path(output_path)
    manifest_path = manifest_path_for(output)
    if not overwrite:
        occupied = [path for path in (output, manifest_path) if path.exists()]
        if occupied:
            joined = ", ".join(str(path) for path in occupied)
            raise OutputExistsError(
                f"refusing to overwrite existing artifact(s): {joined}; pass --overwrite"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _reserve_temp(output)
    try:
        _write_records_temp(records, temp_path, output.suffix.casefold())
        output_hash = sha256_file(temp_path)
        complete_manifest = dict(manifest)
        complete_manifest["output"] = {
            "path": str(output.resolve()),
            "format": output.suffix.casefold().lstrip("."),
            "row_count": len(records),
            "sha256": output_hash,
        }
        manifest_payload = json.dumps(
            complete_manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ).encode("utf-8") + b"\n"
        _commit_complete_file(temp_path, output, overwrite=overwrite)
        atomic_write_bytes(manifest_path, manifest_payload, overwrite=overwrite)
    finally:
        temp_path.unlink(missing_ok=True)
    return output, manifest_path


def build_manifest(
    *,
    command: str,
    profile_path: str | Path,
    profile_id: str,
    profile_version: str,
    domain: str,
    input_paths: Sequence[str | Path],
    parameters: Mapping[str, Any],
    counts: Mapping[str, int],
) -> dict[str, Any]:
    profile = Path(profile_path)
    inputs = [Path(path) for path in input_paths]
    return {
        "manifest_schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "profile": {
            "path": str(profile.resolve()),
            "profile_id": profile_id,
            "profile_version": profile_version,
            "domain": domain,
            "sha256": sha256_file(profile),
        },
        "inputs": [
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
                # Scientific source data is read-only by contract. The filtering
                # commands only create new derived artifacts and never rewrite a
                # source Parquet/JSON file.
                "immutable_source": True,
            }
            for path in inputs
        ],
        "parameters": dict(parameters),
        "counts": dict(counts),
        "source_data_policy": "read_only_immutable",
    }


def read_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    suffix = source.suffix.casefold()
    if suffix in {".json", ".txt"}:
        with source.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if isinstance(raw, dict) and isinstance(raw.get("records"), list):
            raw = raw["records"]
        if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
            raise ValueError(f"{source}: expected a JSON array of objects")
        return [dict(item) for item in raw]
    if suffix in {".jsonl", ".ndjson"}:
        records: list[dict[str, Any]] = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"{source}:{line_number}: expected a JSON object")
                records.append(item)
        return records
    if suffix == ".csv":
        with source.open("r", encoding="utf-8", newline="") as handle:
            return [dict(item) for item in csv.DictReader(handle)]
    if suffix == ".parquet":
        try:
            import pandas as pd
        except ImportError as error:  # pragma: no cover - project dependency guard
            raise RuntimeError("reading Parquet requires the project's pandas/pyarrow dependencies") from error
        return pd.read_parquet(source).to_dict(orient="records")
    raise ValueError(f"unsupported input format '{suffix}'")
