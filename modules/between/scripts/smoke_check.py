"""Exercise essential workflows using synthetic data only."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.demo import create_demo
from app.domain import Conflict, Invalid
from app.exporting import export_session
from app.reader import SamplingRunReader
from app.service import AnnotationService
from app.service import CHECKLIST
from app.storage import Store


def check():
    scratch = Path(__file__).resolve().parents[1] / "workspace" / "smoke"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tangletrace-between-smoke-", dir=scratch) as temp:
        assert Path(temp).resolve().is_relative_to(scratch.resolve())
        store = Store(temp)
        reader = SamplingRunReader(store)
        imported = reader.import_run(str(create_demo(store.root)))
        assert reader.import_run(str(create_demo(store.root)))["reused"]
        service = AnnotationService(store)
        sample = service.windows(imported["import_id"])[0]["sample_id"]
        session = service.open_session(imported["import_id"], sample, "annotator-a")
        other = service.open_session(imported["import_id"], sample, "annotator-b")
        sid = session["id"]
        assert service.state(sid)["progress"] == {"confirmed": 0, "total": 9, "active_ms": 0}
        assert service.state(sid)["messages"][3]["window_role"] == "context"
        d = {"source_status": "complete", "edges": [{"target_message_id": "P01"}]}
        saved = service.draft(sid, "P03", d, 0)
        assert service.state(sid)["progress"]["confirmed"] == 0
        try:
            service.draft(sid, "P03", d, 0)
            raise AssertionError("Concurrent draft was accepted")
        except Conflict:
            pass
        state = service.confirm(sid, "P03", d, 0, 1000, saved["updated_at"])
        assert state["components"][0]["message_ids"] == ["P01", "P03"]
        sig = state["components"][0]["signature"]
        state = service.review_component(sid, sig, 1)
        assert state["components"][0]["reviewed"]
        state = service.confirm(sid, "P05", {"source_status": "complete", "edges": [{"target_message_id": "P02"}]}, 1)
        assert len(state["components"]) == 2 and state["components"][0]["reviewed"]
        state = service.confirm(sid, "P10", {"source_status": "complete", "edges": [{"target_message_id": "P03"}, {"target_message_id": "P05"}]}, 2)
        assert len(state["components"]) == 1 and not state["components"][0]["reviewed"]
        state = service.undo(sid, 3)
        assert len(state["components"]) == 2
        state = service.undo(sid, 4, redo=True)
        assert len(state["components"]) == 1
        for source, target in (("P03", "P12"), ("P01", "P02"), ("P03", "P03"), ("P03", "INVISIVEL")):
            try:
                service.confirm(sid, source, {"source_status": "complete", "edges": [{"target_message_id": target}]}, 5)
                raise AssertionError("Invalid edge was accepted")
            except Invalid:
                pass
        state = service.confirm(sid, "P11", {"source_status": "new_conversation", "edges": []}, 5)
        assert len(state["components"]) == 2
        state = service.confirm(sid, "P06", {"source_status": "complete", "edges": [{"target_message_id": "P03", "ambiguous": True}]}, 6)
        assert "P06" in state["unassigned"]
        assert service.state(other["id"])["progress"]["confirmed"] == 0
        # The last consistent state remains after creating another store instance.
        restored = AnnotationService(Store(temp)).state(sid)
        assert restored["session"]["graph_revision"] == 7
        result = export_session(service, sid, 7)
        assert result["manifest"]["counts"]["annotations"] == 5
        assert result["manifest"]["status"] == "work_in_progress"
        assert (Path(result["directory"]) / "derived" / "human_reply_components.parquet").is_file()
        # Global review and a third adjudication session without merging the bases.
        for original in (sid, other["id"]):
            current = service.state(original)
            for mid in list(current["pending"]):
                current = service.confirm(original, mid, {"source_status": "no_reply", "edges": []}, current["session"]["graph_revision"])
        comparison = service.compare(sid, other["id"])
        assert comparison["comparable_sources"] > 0
        consolidated = service.open_session(imported["import_id"], sample, "adjudicador", "Consolidada", "adjudication", [sid, other["id"]])
        current = service.state(consolidated["id"])
        for mid in list(current["pending"]):
                current = service.confirm(consolidated["id"], mid, {"source_status": "no_reply", "edges": [], "notes": "Synthetic decision to verify adjudication."}, current["session"]["graph_revision"])
        current = service.review_interval(consolidated["id"], {k: True for k in CHECKLIST}, current["session"]["graph_revision"])
        assert current["validated"]
        release = export_session(service, consolidated["id"], current["session"]["graph_revision"])
        assert release["manifest"]["release_type"] == "adjudicated_gold"
        print("OK: import, drafts, conflicts, context, multiple parents, review, merge, undo/redo, isolation, recovery, and export through the materializer.")


if __name__ == "__main__":
    check()
