from __future__ import annotations

import csv
import json
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import __version__
from .domain import Invalid, canonical
from .reader import sha256_file
from .storage import event
from .vendor import annotation_bundle as legacy


def export_session(service, session_id, expected_revision):
    """Export a confirmed snapshot; never overwrite an export or include drafts."""
    backup_path = service.store.backup()
    export_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8]
    root = service.store.root / "exports" / export_id
    root.mkdir(parents=True, exist_ok=False)
    try:
        with service.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            session, meta, messages, decisions = service._load(db, session_id)
            service._check_revision(session, expected_revision)
            graph = service._graph_state(db, session, messages, decisions)
            if session["kind"] == "adjudication":
                service._check_bases(db, session)
                if not graph["validated"]:
                    raise Invalid("An adjudicated release requires review and global validation before export.")
            stage = root / "source_window.csv"
            fields = ["annotation_id", "guild_id", "channel_id", "guild_name", "channel_name", "messages_json"]
            with stage.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({**{k: meta.get(k, "") for k in fields[:-1]}, "messages_json": canonical(messages)})
            inputs, human, derived, reviews = [root / name for name in ("inputs_compat", "human", "derived", "reviews")]
            human.mkdir()
            reviews.mkdir()
            legacy.build_annotation_bundle(stage, inputs)
            stage.rename(inputs / "source_window.csv")
            statuses = pd.read_parquet(inputs / "source_statuses.parquet")
            annotation_rows = []
            extensions = []
            for index, row in statuses.iterrows():
                mid = row["source_message_id"]
                d = decisions[mid]
                statuses.loc[index, "annotator_id"] = session["annotator_id"]
                statuses.loc[index, "source_status"] = d["source_status"]
                statuses.loc[index, "ambiguous"] = d["source_status"] == "ambiguous"
                statuses.loc[index, "confidence"] = d["confidence"]
                statuses.loc[index, "notes"] = d["notes"]
                for edge in d["edges"]:
                    annotation_rows.append({"sample_id": session["sample_id"], "source_message_id": mid,
                                            "annotator_id": session["annotator_id"],
                                            **edge})
                extensions.append({"session_id": session_id, "source_message_id": mid,
                                   "unresolved_additional_relation": d.get("unresolved_additional_relation", False),
                                   "unresolved_reason": d.get("unresolved_reason", "")})
            annotations = pd.DataFrame.from_records(annotation_rows, columns=legacy.ANNOTATION_COLUMNS) if annotation_rows else legacy._empty_annotations()
            annotations.to_parquet(human / "annotations.parquet", index=False)
            statuses.to_parquet(human / "source_statuses.parquet", index=False)
            # Avoid duplicate human tables with conflicting states.
            (inputs / "annotations.parquet").unlink()
            (inputs / "source_statuses.parquet").unlink()
            legacy.materialize_annotation_tables(inputs / "messages.parquet", inputs / "sample_messages.parquet",
                                               human / "annotations.parquet", human / "source_statuses.parquet", derived)
            result = pd.read_parquet(derived / "human_reply_components.parquet")
            expected = {(c["conversation_id"], mid) for c in graph["components"] for mid in c["message_ids"]}
            actual = set(zip(result["conversation_id"], result["message_id"]))
            if expected != actual:
                raise Invalid("The interface derivation differs from the materializer. Export aborted.")
            pd.DataFrame(extensions).to_parquet(reviews / "source_extensions.parquet", index=False)
            pd.DataFrame([{"message_id": m["message_id"], "payload_json": canonical(m)} for m in messages]).to_parquet(inputs / "message_payloads.parquet", index=False)
            pd.DataFrame([{"sample_id": session["sample_id"], "message_id": m["message_id"],
                           "sequence": m["sequence"], "window_role": m["window_role"],
                           "requires_reply_annotation": m["requires_reply_annotation"],
                           "target_inclusion_probability": m.get("target_inclusion_probability"),
                           "target_design_weight": m.get("target_design_weight")} for m in messages]).to_parquet(inputs / "sampling_memberships.parquet", index=False)
            pd.DataFrame([session]).to_parquet(reviews / "annotation_sessions.parquet", index=False)
            for table in ("events", "conversation_reviews", "interval_reviews", "adjudication_records"):
                frame = pd.read_sql_query(f"SELECT * FROM {table} WHERE session_id=? ORDER BY id", db, params=(session_id,))
                name = "annotation_events" if table == "events" else table
                frame.to_parquet(reviews / (name + ".parquet"), index=False)
            imported = db.execute("SELECT * FROM imports WHERE id=?", (session["import_id"],)).fetchone()
            provenance = json.loads(imported["provenance"])
            (inputs / "sample_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            codebook = Path(__file__).resolve().parent / "vendor" / "CODEBOOK.md"
            if codebook.is_file():
                shutil.copy2(codebook, root / "CODEBOOK.md")
            # Keep references usable after extracting the ZIP to another location.
            for summary_path in (inputs / "annotation_bundle_summary.json", derived / "human_annotation_summary.json"):
                if summary_path.is_file():
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    for key, value in summary.items():
                        if isinstance(value, str) and value.startswith(str(root)):
                            summary[key] = "inputs_compat/source_window.csv" if value == str(stage) else str(Path(value).relative_to(root)).replace("\\", "/")
                    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            release = "adjudicated_gold" if session["kind"] == "adjudication" else "single_annotator"
            manifest = {"export_id": export_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "tool_version": __version__, "codebook_version": "1.1", "release_type": release,
                        "status": "validated" if graph["validated"] and not graph["drafts"] else "work_in_progress",
                        "session_id": session_id, "annotator_id": session["annotator_id"],
                        "sample_id": session["sample_id"], "import_id": session["import_id"],
                        "graph_revision": expected_revision, "base_sessions": json.loads(session["base_sessions"]),
                        "source_manifest_hash": provenance.get("source_manifest_hash"),
                        "source_hashes": provenance["hashes"], "edge_direction": "response_source_to_antecedent_target",
                        "include_ambiguous_in_components": False, "drafts_excluded": True,
                        "boundary_status": "unverified; observed components within sampled window",
                        "operational_extensions": "source_extensions.parquet; no change to codebook v1.1",
                        "materializer_sha256": sha256_file(Path(legacy.__file__)),
                        "counts": {"targets": len(decisions), "confirmed": len(decisions) - len(graph["pending"]),
                                   "annotations": len(annotations), "components": len(graph["components"])}}
            # Human-readable summary derived from the same confirmed Parquet snapshot.
            counts = dict(manifest["counts"])
            counts.update({"status_" + status: sum(d["source_status"] == status for d in decisions.values())
                           for status in ("pending", "complete", "no_reply", "outside_context", "ambiguous", "new_conversation")})
            counts["ambiguous_edges"] = sum(bool(edge["ambiguous"]) for d in decisions.values() for edge in d["edges"])
            counts["drafts_excluded"] = len(graph["drafts"])
            counts["context_messages"] = sum(not m["requires_reply_annotation"] for m in messages)
            summary = {"session_id": session_id, "annotator_id": session["annotator_id"],
                       "sample_id": session["sample_id"], "status": manifest["status"],
                       "release_type": release, "graph_revision": expected_revision, **counts}
            (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with (root / "summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["metric", "value"])
                # Arbitrary IDs stay in JSON; the CSV contains numeric metrics only.
                writer.writerows(counts.items())
            manifest["outputs"] = {str(p.relative_to(root)).replace("\\", "/"): sha256_file(p)
                                   for p in sorted(root.rglob("*")) if p.is_file()}
            (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            event(db, session, "export_created", after={"export_id": export_id, "release_type": release,
                                                        "manifest_sha256": sha256_file(root / "manifest.json")})
        archive = root.with_suffix(".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zipped.write(path, path.relative_to(root))
        return {"export_id": export_id, "directory": str(root),
                "manifest": manifest}
    except BaseException:
        # Keep an incomplete export for diagnosis without presenting it as valid.
        (root / "INCOMPLETE.txt").write_text("Export incomplete. Do not use as a validated dataset.\n", encoding="utf-8")
        raise
