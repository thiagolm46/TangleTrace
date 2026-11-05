"""Desktop worker: one JSON line per request over stdin/stdout, without networking.

stdout is reserved for the protocol. Diagnostics go to stderr.
Closing stdin stops the worker; an OS lock prevents concurrent workers on one database.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys

MAX_REQUEST = 2 * 1024 * 1024


class WorkspaceLock:
    def __init__(self, workspace):
        Path(workspace).mkdir(parents=True, exist_ok=True)
        self.file = open(Path(workspace) / ".desktop.lock", "a+b")
        self.file.seek(0)
        if not self.file.read(1):
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError("This workspace is already open in another desktop instance. Close it before continuing.") from None

    def close(self):
        self.file.close()  # The OS releases the lock even after a failure.


def main():
    parser = argparse.ArgumentParser(description="TangleTrace BETWEEN: local annotation processing")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--source", default="")
    args = parser.parse_args()
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8")
    wire = sys.stdout
    sys.stdout = sys.stderr  # Includes output from import threads.
    lock, app, startup_error = None, None, None
    # Redirect library import output as well, keeping the JSON protocol clean.
    with redirect_stdout(sys.stderr):
        try:
            from .application import Application
            lock = WorkspaceLock(args.workspace)
            app = Application(args.workspace, args.source)
        except Exception as exc:
            startup_error = str(exc)
    try:
        while True:
            line = sys.stdin.buffer.readline(MAX_REQUEST + 1)
            if not line:
                break
            response, request_id = None, None
            try:
                if len(line) > MAX_REQUEST:
                    raise ValueError("Request exceeds 2 MiB.")
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("Invalid request.")
                request_id = request.get("id")
                if startup_error:
                    raise RuntimeError(startup_error)
                with redirect_stdout(sys.stderr):
                    result = app.request(request["method"], request.get("params", {}))
                response = {"id": request_id, "ok": True, "result": result}
            except Exception as exc:
                response = {"id": request_id, "ok": False, "error": {"kind": type(exc).__name__, "message": str(exc)}}
            wire.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
            wire.flush()
            if len(line) > MAX_REQUEST or (app and app.closed):
                break
    finally:
        if lock:
            lock.close()


if __name__ == "__main__":
    main()
