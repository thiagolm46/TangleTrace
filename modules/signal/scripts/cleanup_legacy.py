from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "data/processed/disentanglement_experiments",
    "data/processed/filtering/games",
    "data/processed/disentanglement/sampling_design_audit_v1",
    "data/processed/disentanglement/sampling_design_audit_v2",
    "discord_disentanglement/approaches",
    "discord_disentanglement/experiments",
    "discord_disentanglement/evaluation",
    "discord_disentanglement/training",
    "discord_disentanglement/ui",
    "configs/approaches",
    "configs/experiments",
)
PRESERVED = (
    "annotations/channel_selection_2026-10-07",
    "data/processed/filtering/software",
    "data/processed/disentanglement/population",
    "data/processed/disentanglement/population_payload_v2",
    "data/processed/disentanglement/population_participants_v2",
    "data/processed/disentanglement/sampling_participants_v2",
    "data/processed/disentanglement/sampling_participants_audit_v2",
    "data/processed/disentanglement/sampling_pilot_v1",
    "data/processed/disentanglement/sampling_design_audit_v3",
    "data/annotation",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _strings(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value.replace("\\", "/")


def cleanup(root: Path, *, apply: bool = False, report: Path | None = None) -> dict:
    root = root.resolve()
    preserved_manifests = {}
    references = []
    for relative in PRESERVED:
        directory = root / relative
        for path in directory.rglob("*.json") if directory.exists() else ():
            preserved_manifests[path.relative_to(root).as_posix()] = sha256(path)
            references.extend(_strings(json.loads(path.read_text(encoding="utf-8"))))
    targets = []
    for relative in TARGETS:
        target = root / relative
        if not target.exists():
            continue
        if target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError(f"unsafe cleanup target: {relative}")
        for reference in references:
            if reference.endswith(relative) or relative + "/" in reference:
                raise ValueError(f"preserved artifact references legacy target: {relative}")
        paths = sorted(target.rglob("*")) if target.is_dir() else [target]
        if any(path.is_symlink() for path in paths):
            raise ValueError(f"symlink inside cleanup target: {relative}")
        files = [path for path in paths if path.is_file()]
        if not relative.startswith("data/") and any(path.suffix != ".pyc" for path in files):
            raise ValueError(f"non-cache source files remain in removed module: {relative}")
        records = [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in files]
        targets.append({"path": relative, "bytes": sum(item["bytes"] for item in records), "files": records})
    result = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if apply else "dry_run",
        "targets": targets,
        "total_bytes": sum(item["bytes"] for item in targets),
        "preserved_manifest_hashes": preserved_manifests,
        "removed": [],
    }
    if not apply:
        return result
    if report is None:
        raise ValueError("--report is required when applying cleanup")
    report = report.resolve()
    if any(report.is_relative_to(root / item["path"]) for item in targets):
        raise ValueError("cleanup report must be outside removal targets")
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    try:
        for item in targets:
            target = root / item["path"]
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            result["removed"].append(item["path"])
        for relative, expected in preserved_manifests.items():
            if sha256(root / relative) != expected:
                raise ValueError(f"preserved manifest changed: {relative}")
        result["preserved_manifests_unchanged"] = True
    finally:
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit or remove only allowlisted obsolete outputs and removed-module caches.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    result = cleanup(ROOT, apply=arguments.apply, report=arguments.report)
    print(json.dumps({"mode": result["mode"], "targets": [{"path": item["path"], "bytes": item["bytes"], "files": len(item["files"])} for item in result["targets"]], "total_bytes": result["total_bytes"], "removed": result["removed"]}, indent=2))


if __name__ == "__main__":
    main()