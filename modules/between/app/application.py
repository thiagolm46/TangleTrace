"""Application use cases exposed to the Tauri host through the Python worker."""
from __future__ import annotations

import secrets
import threading
from pathlib import Path

from . import __version__
from .demo import create_demo
from .domain import Invalid
from .exporting import export_session
from .reader import SamplingRunReader
from .service import AnnotationService
from .storage import Store

class Application:
    def __init__(self, workspace, default_source=""):
        self.store = Store(workspace)
        self.service = AnnotationService(self.store)
        self.reader = SamplingRunReader(self.store)
        self.default_source = default_source
        self.jobs, self.job_lock = {}, threading.Lock()
        self.import_lock = threading.Lock()
        self.closed = False

    def _update_job(self, job_id, **values):
        with self.job_lock:
            self.jobs[job_id].update(values)

    def import_async(self, path):
        with self.job_lock:
            if self.closed:
                raise Invalid("The workspace is shutting down.")
            if any(job["status"] == "running" for job in self.jobs.values()):
                raise Invalid("Wait for the current import to finish before opening another sample.")
            job_id = secrets.token_hex(12)
            self.jobs[job_id] = {"status": "running", "message": "Checking the local sample…", "count": 0}

        def run():
            try:
                with self.import_lock:
                    def update(message, count):
                        self._update_job(job_id, message=message, count=count)
                    result = self.reader.import_run(path, update)
                self._update_job(job_id, status="done", result=result)
            except Exception as exc:
                self._update_job(job_id, status="error", message=str(exc))
        threading.Thread(target=run, name="sample-import", daemon=True).start()
        return {"job_id": job_id}

    def ensure_idle(self):
        with self.job_lock:
            if any(job["status"] == "running" for job in self.jobs.values()):
                raise Invalid("An import is in progress. Wait for it to finish.")
        return {"idle": True}

    def shutdown(self):
        self.ensure_idle()
        self.closed = True
        return {"closed": True}

    def request(self, method, data=None):
        if self.closed:
            raise Invalid("The workspace has already shut down.")
        d = {} if data is None else data
        if not isinstance(d, dict):
            raise Invalid("Parameters must be a JSON object.")
        s, sid, revision = self.service, d.get("session_id"), d.get("expected_revision")
        if method == "config":
                return {"version": __version__, "protocol_version": 1,
                    "default_source": self.default_source, "workspace": str(self.store.root),
                    "database": str(self.store.path), "exports": str(self.store.root / "exports")}
        if method == "imports": return s.imports()
        if method == "windows": return s.windows(d["import_id"], d.get("annotator_id", ""))
        if method == "state": return s.state(d["session_id"])
        if method == "sessions": return s.sessions(d["import_id"], d["sample_id"])
        if method == "compare": return s.compare(d["left"], d["right"])
        if method == "history": return s.history(d["session_id"])
        if method == "job":
            with self.job_lock:
                return dict(self.jobs.get(d["job_id"], {"status": "error", "message": "Import job not found."}))
        if method == "import": return self.import_async(d["path"])
        if method == "demo":
            self.ensure_idle()
            return self.import_async(str(create_demo(self.store.root)))
        if method == "open_session":
            return s.open_session(d["import_id"], d["sample_id"], d["annotator_id"], d.get("label", "Primary"), d.get("kind", "single_annotator"), d.get("bases"))
        if method == "cursor": return s.cursor(sid, d["source_id"])
        if method == "draft": return s.draft(sid, d["source_id"], d["decision"], revision, d.get("expected_draft_updated"))
        if method == "discard_draft": return s.discard_draft(sid, d["source_id"], d.get("expected_draft_updated"))
        if method == "confirm": return s.confirm(sid, d["source_id"], d["decision"], revision, d.get("active_ms", 0), d.get("expected_draft_updated"))
        if method in {"undo", "redo"}: return s.undo(sid, revision, redo=method == "redo")
        if method == "review_component": return s.review_component(sid, d["signature"], revision)
        if method == "review_interval": return s.review_interval(sid, d["checklist"], revision)
        if method == "export": return export_session(s, sid, revision)
        if method == "backup": return {"path": str(self.store.backup())}
        if method == "ensure_idle": return self.ensure_idle()
        if method == "shutdown": return self.shutdown()
        raise Invalid("Unknown command: " + str(method))
