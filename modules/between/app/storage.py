from __future__ import annotations

import json
import sqlite3
import zlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .domain import canonical


def now():
    return datetime.now(timezone.utc).isoformat()


def pack(value):
    return zlib.compress(canonical(value).encode("utf-8"), 3)


def unpack(value):
    return json.loads(zlib.decompress(value))


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "annotations.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS imports (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, source_path TEXT NOT NULL,
                    created_at TEXT NOT NULL, provenance TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS windows (
                    import_id TEXT NOT NULL REFERENCES imports(id), id TEXT NOT NULL,
                    metadata TEXT NOT NULL, payload BLOB NOT NULL, signature TEXT NOT NULL,
                    target_count INTEGER NOT NULL, context_count INTEGER NOT NULL,
                    PRIMARY KEY(import_id,id));
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, import_id TEXT NOT NULL, sample_id TEXT NOT NULL,
                    annotator_id TEXT NOT NULL, label TEXT NOT NULL, kind TEXT NOT NULL,
                    graph_revision INTEGER NOT NULL DEFAULT 0, cursor TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    base_sessions TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY(import_id,sample_id) REFERENCES windows(import_id,id));
                CREATE TABLE IF NOT EXISTS decisions (
                    session_id TEXT NOT NULL REFERENCES sessions(id), source_id TEXT NOT NULL,
                    data TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(session_id,source_id));
                CREATE TABLE IF NOT EXISTS drafts (
                    session_id TEXT NOT NULL REFERENCES sessions(id), source_id TEXT NOT NULL,
                    data TEXT NOT NULL, base_revision INTEGER NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(session_id,source_id));
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL, event_type TEXT NOT NULL, source_id TEXT,
                    before_data TEXT, after_data TEXT, revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL, active_ms INTEGER NOT NULL DEFAULT 0,
                    undo_of INTEGER, redone_by INTEGER);
                CREATE TABLE IF NOT EXISTS conversation_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    signature TEXT NOT NULL, graph_revision INTEGER NOT NULL,
                    actor_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS interval_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    graph_revision INTEGER NOT NULL, checklist TEXT NOT NULL,
                    actor_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS adjudication_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    source_id TEXT NOT NULL, bases TEXT NOT NULL, rationale TEXT NOT NULL,
                    graph_revision INTEGER NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS histories (
                    session_id TEXT PRIMARY KEY, undo_stack TEXT NOT NULL DEFAULT '[]',
                    redo_stack TEXT NOT NULL DEFAULT '[]');
                CREATE INDEX IF NOT EXISTS sessions_by_window ON sessions(import_id,sample_id);
                CREATE INDEX IF NOT EXISTS events_by_session ON events(session_id,id);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def backup(self):
        path = self.root / "backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".sqlite3")
        path.parent.mkdir(exist_ok=True)
        with self.connect() as source, sqlite3.connect(path) as target:
            source.backup(target)
        return path


def event(db, session, event_type, source_id=None, before=None, after=None, active_ms=0, undo_of=None):
    return db.execute(
        "INSERT INTO events(session_id,actor_id,event_type,source_id,before_data,after_data,revision,created_at,active_ms,undo_of) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (session["id"], session["annotator_id"], event_type, source_id,
         canonical(before) if before is not None else None,
         canonical(after) if after is not None else None, session["graph_revision"], now(), active_ms, undo_of)
    ).lastrowid
