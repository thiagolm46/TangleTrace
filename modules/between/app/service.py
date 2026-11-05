from __future__ import annotations

import json
import uuid

from .domain import Conflict, Invalid, canonical, compare_annotations, derive, empty_decision, validate_decision
from .storage import event, now, unpack

CHECKLIST = ("sources", "components", "unassigned", "interleaving", "uncertainty", "boundaries")


class AnnotationService:
    def __init__(self, store):
        self.store = store

    def imports(self):
        with self.store.connect() as db:
            return [{**dict(r), "provenance": json.loads(r["provenance"])} for r in db.execute("SELECT * FROM imports ORDER BY created_at DESC")]

    def windows(self, import_id, annotator_id=""):
        with self.store.connect() as db:
            rows = db.execute("SELECT id,metadata,target_count,context_count FROM windows WHERE import_id=? ORDER BY id", (import_id,)).fetchall()
            result = []
            for row in rows:
                sessions = []
                for s in db.execute("SELECT * FROM sessions WHERE import_id=? AND sample_id=? AND annotator_id=? ORDER BY updated_at DESC", (import_id, row["id"], annotator_id)).fetchall():
                    n = db.execute("SELECT count(*) FROM decisions WHERE session_id=? AND json_extract(data,'$.source_status')!='pending'", (s["id"],)).fetchone()[0]
                    validated = db.execute("SELECT 1 FROM interval_reviews WHERE session_id=? AND graph_revision=? AND status='validated'", (s["id"], s["graph_revision"])).fetchone() is not None
                    sessions.append({**dict(s), "confirmed": n, "validated": validated})
                result.append({**json.loads(row["metadata"]), "sessions": sessions})
            return result

    def open_session(self, import_id, sample_id, annotator_id, label="Primary", kind="single_annotator", bases=None):
        annotator_id, label = annotator_id.strip(), label.strip() or "Primary"
        if not annotator_id or len(annotator_id) > 100:
            raise Invalid("Enter an annotator identifier (up to 100 characters).")
        if kind not in {"single_annotator", "adjudication"}:
            raise Invalid("Invalid session type.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM windows WHERE import_id=? AND id=?", (import_id, sample_id)).fetchone():
                raise Invalid("Window not found.")
            existing = db.execute("SELECT * FROM sessions WHERE import_id=? AND sample_id=? AND annotator_id=? AND label=? AND kind=?", (import_id, sample_id, annotator_id, label, kind)).fetchone()
            if existing:
                if kind == "adjudication":
                    current_bases = [{"session_id": sid, "graph_revision": self._load(db, sid)[0]["graph_revision"]} for sid in (bases or [])]
                    saved_bases = [{k: b[k] for k in ("session_id", "graph_revision")} for b in json.loads(existing["base_sessions"])]
                    if sorted(current_bases, key=lambda x: x["session_id"]) != sorted(saved_bases, key=lambda x: x["session_id"]):
                        raise Conflict("An adjudication with this label and different base revisions already exists. Use a new label.")
                event(db, existing, "session_resumed")
                return dict(existing)
            base_versions = []
            if kind == "adjudication":
                if not bases or len(set(bases)) < 2:
                    raise Invalid("Select at least two independent sessions.")
                actors = set()
                for sid in bases:
                    s, _, _, _ = self._load(db, sid)
                    if s["import_id"] != import_id or s["sample_id"] != sample_id or s["kind"] != "single_annotator":
                        raise Invalid("Base sessions must be independent annotations of the same window.")
                    actors.add(s["annotator_id"])
                    base_versions.append({"session_id": sid, "graph_revision": s["graph_revision"],
                                          "annotator_id": s["annotator_id"]})
                if len(actors) < 2:
                    raise Invalid("Adjudication requires at least two distinct annotators in the base sessions.")
            sid, timestamp = uuid.uuid4().hex, now()
            db.execute("INSERT INTO sessions(id,import_id,sample_id,annotator_id,label,kind,created_at,updated_at,base_sessions) VALUES(?,?,?,?,?,?,?,?,?)",
                       (sid, import_id, sample_id, annotator_id, label, kind, timestamp, timestamp, canonical(base_versions)))
            s = dict(db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone())
            db.execute("INSERT INTO histories(session_id) VALUES(?)", (sid,))
            event(db, s, "session_created", after={"kind": kind, "bases": base_versions})
            return s

    def _load(self, db, session_id):
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            raise Invalid("Session not found.")
        s = dict(row)
        window = db.execute("SELECT metadata,payload FROM windows WHERE import_id=? AND id=?", (s["import_id"], s["sample_id"])).fetchone()
        messages = unpack(window["payload"])
        decisions = {m["message_id"]: empty_decision() for m in messages if m["requires_reply_annotation"]}
        decisions.update({r["source_id"]: json.loads(r["data"]) for r in db.execute("SELECT source_id,data FROM decisions WHERE session_id=?", (session_id,))})
        return s, json.loads(window["metadata"]), messages, decisions

    def _check_revision(self, session, expected):
        if not isinstance(expected, int) or expected != session["graph_revision"]:
            raise Conflict("The session changed in another tab. Reload before editing; the confirmed state was preserved.")

    def _graph_state(self, db, s, messages, decisions):
        components = derive(messages, decisions)
        reviews = {r["signature"] for r in db.execute("SELECT signature FROM conversation_reviews WHERE session_id=? AND status='reviewed'", (s["id"],))}
        for component in components:
            component["reviewed"] = component["signature"] in reviews
        assigned = {mid for c in components for mid in c["message_ids"]}
        pending = [mid for mid, d in decisions.items() if d["source_status"] == "pending"]
        drafts = {r["source_id"]: {"decision": json.loads(r["data"]), "base_revision": r["base_revision"], "updated_at": r["updated_at"]} for r in db.execute("SELECT * FROM drafts WHERE session_id=?", (s["id"],))}
        validated = not drafts and db.execute("SELECT 1 FROM interval_reviews WHERE session_id=? AND graph_revision=? AND status='validated'", (s["id"], s["graph_revision"])).fetchone() is not None
        return {"components": components, "pending": pending, "drafts": drafts,
                "unassigned": [m["message_id"] for m in messages if m["message_id"] not in assigned],
                "validated": validated,
                "ready_for_review": not pending and not drafts,
                "review_blockers": ([f"{len(pending)} pending message(s)"] if pending else []) +
                    ([f"{len(drafts)} open draft(s)"] if drafts else []) +
                    ([f"{sum(not c['reviewed'] for c in components)} conversation(s) not reviewed"] if any(not c["reviewed"] for c in components) else [])}

    def state(self, session_id):
        with self.store.connect() as db:
            s, meta, messages, decisions = self._load(db, session_id)
            graph = self._graph_state(db, s, messages, decisions)
            total = len(decisions)
            active_ms = db.execute("SELECT coalesce(sum(active_ms),0) FROM events WHERE session_id=?", (session_id,)).fetchone()[0]
            return {"session": s, "window": meta, "messages": messages, "decisions": decisions, **graph,
                    "progress": {"confirmed": total - len(graph["pending"]), "total": total,
                                 "active_ms": active_ms}, "checklist_keys": CHECKLIST}

    def cursor(self, session_id, source_id):
        with self.store.connect() as db:
            s, _, _, decisions = self._load(db, session_id)
            if source_id not in decisions:
                raise Invalid("The work cursor must point to a target message.")
            db.execute("UPDATE sessions SET cursor=?,updated_at=? WHERE id=?", (source_id, now(), session_id))
        return {"saved": True}

    def _check_draft(self, db, session_id, source_id, expected_updated):
        row = db.execute("SELECT updated_at FROM drafts WHERE session_id=? AND source_id=?", (session_id, source_id)).fetchone()
        actual = row["updated_at"] if row else None
        if actual != expected_updated:
            raise Conflict("This message's draft changed in another tab. Reload to inspect the saved version; your local edit was not overwritten.")

    def draft(self, session_id, source_id, data, expected_revision, expected_updated=None):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            s, _, messages, decisions = self._load(db, session_id)
            self._check_revision(s, expected_revision)
            self._check_draft(db, session_id, source_id, expected_updated)
            valid = validate_decision(messages, source_id, data)
            timestamp = None
            if valid == decisions[source_id]:
                db.execute("DELETE FROM drafts WHERE session_id=? AND source_id=?", (session_id, source_id))
            else:
                timestamp = now()
                db.execute("INSERT INTO drafts VALUES(?,?,?,?,?) ON CONFLICT(session_id,source_id) DO UPDATE SET data=excluded.data,base_revision=excluded.base_revision,updated_at=excluded.updated_at",
                           (session_id, source_id, canonical(valid), expected_revision, timestamp))
            return {"saved": True, "updated_at": timestamp}

    def discard_draft(self, session_id, source_id, expected_updated=None):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._check_draft(db, session_id, source_id, expected_updated)
            db.execute("DELETE FROM drafts WHERE session_id=? AND source_id=?", (session_id, source_id))
        return {"saved": True}

    def _commit_decision(self, db, s, messages, decisions, source_id, valid, event_type, active_ms=0, undo_of=None):
        previous = decisions[source_id]
        if previous == valid:
            db.execute("DELETE FROM drafts WHERE session_id=? AND source_id=?", (s["id"], source_id))
            return None
        s["graph_revision"] += 1
        db.execute("INSERT INTO decisions VALUES(?,?,?,?) ON CONFLICT(session_id,source_id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at", (s["id"], source_id, canonical(valid), now()))
        db.execute("DELETE FROM drafts WHERE session_id=? AND source_id=?", (s["id"], source_id))
        db.execute("UPDATE sessions SET graph_revision=?,updated_at=? WHERE id=?", (s["graph_revision"], now(), s["id"]))
        decisions[source_id] = valid
        sigs = {c["signature"] for c in derive(messages, decisions)}
        invalidated = 0
        for row in db.execute("SELECT id,signature FROM conversation_reviews WHERE session_id=? AND status='reviewed'", (s["id"],)).fetchall():
            if row["signature"] not in sigs:
                db.execute("UPDATE conversation_reviews SET status='invalidated' WHERE id=?", (row["id"],))
                invalidated += 1
        db.execute("UPDATE interval_reviews SET status='invalidated' WHERE session_id=? AND status='validated'", (s["id"],))
        if invalidated:
            event(db, s, "review_invalidated", after={"components": invalidated})
        event_id = event(db, s, event_type, source_id, previous, valid, active_ms, undo_of)
        if s["kind"] == "adjudication":
            if valid["source_status"] != "pending" and not valid["notes"].strip():
                raise Invalid("Enter a rationale in the adjudicated decision notes.")
            db.execute("INSERT INTO adjudication_records(session_id,source_id,bases,rationale,graph_revision,created_at) VALUES(?,?,?,?,?,?)", (s["id"], source_id, s["base_sessions"], valid["notes"], s["graph_revision"], now()))
        return event_id

    def confirm(self, session_id, source_id, data, expected_revision, active_ms=0, expected_draft_updated=None):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            s, _, messages, decisions = self._load(db, session_id)
            self._check_revision(s, expected_revision)
            self._check_draft(db, session_id, source_id, expected_draft_updated)
            valid = validate_decision(messages, source_id, data)
            active_ms = max(0, min(int(active_ms), 3600000))
            eid = self._commit_decision(db, s, messages, decisions, source_id, valid, "decision_confirmed", active_ms)
            if eid:
                h = db.execute("SELECT * FROM histories WHERE session_id=?", (session_id,)).fetchone()
                undo = json.loads(h["undo_stack"]) if h else []
                undo.append(eid)
                db.execute("INSERT INTO histories VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET undo_stack=excluded.undo_stack,redo_stack=excluded.redo_stack", (session_id, canonical(undo), "[]"))
        return self.state(session_id)

    def undo(self, session_id, expected_revision, redo=False):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            s, _, messages, decisions = self._load(db, session_id)
            self._check_revision(s, expected_revision)
            if db.execute("SELECT 1 FROM drafts WHERE session_id=?", (session_id,)).fetchone():
                raise Invalid("Confirm or discard drafts before undoing/redoing a confirmation.")
            h = db.execute("SELECT * FROM histories WHERE session_id=?", (session_id,)).fetchone()
            undo, redos = (json.loads(h["undo_stack"]), json.loads(h["redo_stack"])) if h else ([], [])
            source_stack, target_stack = (redos, undo) if redo else (undo, redos)
            if not source_stack:
                raise Invalid("Nothing to redo." if redo else "No confirmation to undo.")
            eid = source_stack.pop()
            old = db.execute("SELECT * FROM events WHERE id=? AND session_id=?", (eid, session_id)).fetchone()
            data = json.loads(old["after_data"] if redo else old["before_data"])
            data = validate_decision(messages, old["source_id"], data)
            self._commit_decision(db, s, messages, decisions, old["source_id"], data, "decision_redone" if redo else "decision_undone", undo_of=eid)
            target_stack.append(eid)
            db.execute("UPDATE histories SET undo_stack=?,redo_stack=? WHERE session_id=?", (canonical(undo), canonical(redos), session_id))
        return self.state(session_id)

    def review_component(self, session_id, component_signature, expected_revision):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            s, _, messages, decisions = self._load(db, session_id)
            self._check_revision(s, expected_revision)
            if component_signature not in {c["signature"] for c in derive(messages, decisions)}:
                raise Conflict("The conversation changed. Inspect the current version before reviewing.")
            if db.execute("SELECT 1 FROM drafts WHERE session_id=?", (session_id,)).fetchone():
                raise Invalid("Confirm or discard drafts before reviewing.")
            db.execute("INSERT INTO conversation_reviews(session_id,signature,graph_revision,actor_id,status,created_at) VALUES(?,?,?,?,?,?)", (session_id, component_signature, expected_revision, s["annotator_id"], "reviewed", now()))
            event(db, s, "conversation_reviewed", after={"signature": component_signature})
        return self.state(session_id)

    def review_interval(self, session_id, checklist, expected_revision):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            s, _, messages, decisions = self._load(db, session_id)
            self._check_revision(s, expected_revision)
            state = self._graph_state(db, s, messages, decisions)
            if state["review_blockers"]:
                raise Invalid("; ".join(state["review_blockers"]))
            if not all(checklist.get(key) is True for key in CHECKLIST):
                raise Invalid("Complete every item in the global review checklist.")
            for mid, d in decisions.items():
                validate_decision(messages, mid, d)
            if s["kind"] == "adjudication":
                self._check_bases(db, s)
            db.execute("INSERT INTO interval_reviews(session_id,graph_revision,checklist,actor_id,status,created_at) VALUES(?,?,?,?,?,?)", (session_id, expected_revision, canonical(checklist), s["annotator_id"], "validated", now()))
            event(db, s, "interval_validated", after={"checklist": checklist})
        return self.state(session_id)

    def _check_bases(self, db, session):
        for base in json.loads(session["base_sessions"]):
            row = db.execute("SELECT graph_revision FROM sessions WHERE id=?", (base["session_id"],)).fetchone()
            if not row or row["graph_revision"] != base["graph_revision"]:
                raise Conflict("A base session changed after adjudication was created. Create a new adjudication for the updated revisions.")
            _, _, _, decisions = self._load(db, base["session_id"])
            if any(d["source_status"] == "pending" for d in decisions.values()) or db.execute("SELECT 1 FROM drafts WHERE session_id=?", (base["session_id"],)).fetchone():
                raise Invalid("Adjudicated validation requires completed base sessions with no drafts.")

    def sessions(self, import_id, sample_id):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM sessions WHERE import_id=? AND sample_id=? ORDER BY created_at", (import_id, sample_id))]

    def compare(self, left_id, right_id):
        with self.store.connect() as db:
            left, _, messages, a = self._load(db, left_id)
            right, _, _, b = self._load(db, right_id)
            if left_id == right_id or (left["sample_id"], left["import_id"]) != (right["sample_id"], right["import_id"]):
                raise Invalid("Select two different sessions from the same window and import.")
            return {"left": left, "right": right, **compare_annotations(messages, a, b)}

    def history(self, session_id):
        with self.store.connect() as db:
            self._load(db, session_id)
            return [dict(r) for r in db.execute("SELECT * FROM events WHERE session_id=? ORDER BY id DESC LIMIT 300", (session_id,))]
