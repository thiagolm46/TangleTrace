# Desktop Migration and Validation

TangleTrace BETWEEN is the renamed continuation of Discord-SE Desktop. Its
legacy application identifier, environment variables, and local preference
keys remain unchanged to preserve existing workspace and configuration
paths. New builds use `tangletrace-between.exe`; existing distributions keep
their original executable name.

## Changes and Preservation

`start.cmd` launches Rust/Tauri. Use cases are exposed to the desktop host through the Python worker protocol. The application uses JSON pipes, a selectable workspace, and local results. The user guide explains drafts, decisions, review, and validation. CSV/JSON summaries complement the Parquet outputs.

The current frontend is React + TypeScript with official Primer React components, replacing the former `app/static` scripts and styles. Run `npm ci` once after updating. Both Windows launch/build scripts compile the frontend before Cargo. Existing packaged executables must be rebuilt to include the new UI. Node.js is not needed to run a packaged distribution.

Code is updated in the existing directory; no new ZIP is created. The SQLite schema, codebook states, IDs, link direction, context and ambiguity rules, signature-based reviews, comparison, and adjudication are preserved. The vendored `annotation_bundle.py` materializer was not changed. Verification does not create real annotations.

## Migrate

1. Create a backup in the previous version and close it.
2. Open the desktop app and select its `workspace` under My files.
3. Enter the same annotator ID and open the previous interval/session.
4. Check an existing decision, draft, and review.
5. Export and inspect the manifest, summary, and human annotation tables.

Browser preferences are not migrated automatically. Decisions, drafts, and history are stored in SQLite. `-Workspace` overrides the selection for that run only; a selection made in the interface is persisted. The application does not silently search for research or test databases.

## Quick Verification

| Check | What it demonstrates |
| --- | --- |
| `cargo check` / `cargo build` | Type checking, compilation, and asset bundling |
| `npm test` | React rendering, native evidence, explicit inclusion, keyboard behavior, draft serialization and failure handling |
| `npm run build` | Strict TypeScript checks and production React assets |
| `desktop_smoke.py` | Real pipes, lock, persistence, resume, conflicts, and synthetic export |
| `Start-Desktop.ps1 -Diagnose -Workspace <folder>` | Rust starts and stops the worker without opening a window |

Quick checks do not cover visual behavior. Exploratory checklist:

1. Open at 1440×900, 1280×720, and below 850 px wide; check scrolling, fields, and confirmation.
2. Select a folder whose path contains spaces and non-ASCII characters; cancel the picker and confirm that state is unchanged.
3. Edit a draft and close immediately; reopen the session and verify recovery.
4. Inspect a reply, locate its reference, add it, and confirm; verify that each action has a distinct effect.
5. Switch workspaces and switch back, confirming that databases remain independent.
6. Export and open the folder; compare counts and manifest status.
7. Open two windows on the same folder; the second must explain the lock.

The packaged distribution must also be exercised on a machine without Python/Rust, with WebView2 installed. A successful build script is not equivalent to validating this condition on another machine.
