# TangleTrace BETWEEN

**Reply-Link Annotation & Review** (`tangletrace-between`)

**TangleTrace: An Auditable Workbench for Discord Conversation Annotation**

BETWEEN is a local annotation tool for **reply-to-antecedent relations**. It accepts sampled windows prepared by **TangleTrace SIGNAL** (`tangletrace-signal`) or another compatible source. This module lives in `modules/between` in the unified [TangleTrace repository](../../README.md); SIGNAL lives in the sibling `modules/signal`. Both modules can run independently. BETWEEN was formerly known as Discord-SE Desktop.

Its Tauri window and Rust host supervise a Python worker over pipes. The desktop application does not start an HTTP server, access Discord, or call AI services.

The architecture is **Tauri 2 + React + TypeScript + Python**. The interface uses the official **Primer React** components and Primer design tokens, with light/dark system themes and English application text. Rust manages the window, file dialogs, active workspace, and lifecycle. Python retains the Parquet/CSV importer, research rules, and existing graph materializer; this refactoring does not reimplement those rules in React or Rust.

## Run from source

On Windows, run `start-desktop.cmd` (or `start.cmd`). The first run builds the desktop host; later runs reuse build artifacts and compile changes. The application opens in its own window.

Development prerequisites: Windows, Node.js 22.12 or later (Node 24 LTS recommended), npm, stable Rust, MSVC/C++ build tools and Windows SDK, Microsoft Edge WebView2 Runtime, and Python 3.12 or later. Frontend dependencies are pinned by `package-lock.json`; Python dependencies are listed in `requirements.txt`. The launcher checks `.venv`, `DISCORD_ANNOTATOR_PYTHON`, and the configured research repository.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
.\Start-Desktop.ps1
```

When Rust dependencies are already cached, run `./Start-Desktop.ps1 -Offline`. To specify input paths explicitly:

```powershell
.\Start-Desktop.ps1 -PythonPath '.\.venv\Scripts\python.exe' -Source 'C:\data\sampling_pilot_v1'
```

Run the module commands below from `modules/between`. The launch and build
scripts use the sibling `../signal` module as their default `-ResearchRoot`.
To use another SIGNAL installation or the original `Toxicity-OSS` data,
pass its path with `-ResearchRoot` to `Start-Desktop.ps1` or
`Build-Desktop.ps1`. The root `Start.ps1` forwards the same arguments.

Dependency installation may require internet access. **Annotation and export work offline** once dependencies are installed. WebView2 uses the runtime installed on Windows; application assets are bundled with the executable.

The Windows launch and distribution scripts run `npm run build` before Cargo, so they always embed the current React assets. They do not install dependencies automatically. `-Offline` applies to Cargo; the installed frontend builds without accessing the network. For frontend development, `npm run dev` starts Vite on port 1420; that preview has no standalone backend. The supported runtime remains the Tauri desktop window, not a browser application.

## Primer React interface

The React root uses Primer `ThemeProvider` and `BaseStyles`, with local light/dark theme styles from `@primer/primitives`. The interface uses `PageLayout` for responsive and resizable panes, `UnderlineNav` for workflow navigation, `ActionList` for intervals and conversations, `FormControl` with Primer inputs, `Dialog` for overlays, and `Flash`, `Label`, `ProgressBar`, and `Spinner` for feedback. Session comparison uses Primer's experimental `DataTable` / `Table` API, pinned with the rest of the library. Custom CSS is limited to application layout, message content, and semantic colors from Primer tokens; there are no hand-built substitutes for Primer controls.

Interface labels, guides, native window titles, and application errors are in English. Imported research content, participant identifiers, file paths, and previously saved user text are preserved verbatim, not translated.

## Resume previous annotations

Close the older application first. In the desktop app, open **My files → Choose another folder** and select the `workspace` folder containing `annotations.sqlite3`. Alternatively:

```powershell
.\Start-Desktop.ps1 -Workspace 'C:\path\to\installation\workspace'
```

No database is moved or merged. The SQLite schema from version 0.2 is reused; sessions, decisions, drafts, reviews, and history are preserved. Browser-stored visual preferences and identity must be selected again; annotations are not deleted.

Without an explicit path, the application uses the last selected folder or `%LOCALAPPDATA%\br.edu.discord-se.annotator\workspace`. The legacy application identifier is intentionally retained so existing workspace and configuration paths remain discoverable. **My files** shows the active path. The verification workspace beside the source code is never selected automatically.

## Workflow

1. Set the annotator identifier and open the sample. The importer validates files and builds a local index.
2. Select an interval. The left pane lists sampled windows, the center shows the chronological stream, and the right pane contains the source message and its decision.
3. Read the context and native replies. Select antecedents or a no-link decision, then confirm.
4. Review reconstructed conversations and validate the interval.
5. Export results and open their folder from the interface.

Drafts are saved automatically, but **only confirmed decisions** become labels. Native replies are evidence; they do not automatically become human links. The built-in guide explains decisions and keyboard shortcuts.

## Local results

Each export creates a new folder under `workspace\exports`:

| File/folder | Contents |
| --- | --- |
| `summary.csv`, `summary.json` | Session counts for targets, states, links, ambiguities, context, and conversations |
| `human/` | Parquet files for human decisions and links |
| `derived/` | Edges and components produced by the existing materializer |
| `inputs_compat/` | Messages, participation records, and window metadata |
| `reviews/` | Reviews, events, and adjudication information |
| `manifest.json` | Versions, hashes, provenance, and export status |

The export also retains the **data** ZIP expected by the pipeline; it is not a new source-code archive. Summaries are descriptive counts, not estimates of toxicity or prevalence in the full corpus. Individual exports may be in progress; adjudicated exports require validation.

## Build a desktop distribution

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\Build-Desktop.ps1 -PythonPath '.\.venv\Scripts\python.exe'
```

The build creates `desktop-build\desktop-<timestamp>\tangletrace-between.exe` and its `worker` folder. Keep them together. Older distributions retain their original executable name. The distribution bundles the Python worker and dependencies and does not require Python or Rust on the target machine. It requires Windows with WebView2. It does not create a ZIP or installer, does not include research data, and is not digitally signed.

## Documentation

- [Reproducibility protocol](docs/REPRODUCIBILITY.md)
- [Architecture and contracts](docs/ARCHITECTURE.md)
- [Annotation flow and rules](docs/ANNOTATION_FLOW.md)
- [User guide](docs/USER_GUIDE.md)
- [Migration and recovery](docs/DESKTOP_MIGRATION.md)
- [Desktop validation record](docs/DESKTOP_VALIDATION.md)
- [Artifact specification](docs/ARTIFACT_SPEC.md) and [codebook](docs/CODEBOOK_v1.1.md)

The supported application is the Tauri desktop build. No HTTP server or browser-only execution path is included.

## Quick checks

```powershell
npm test
npm run build
cargo check --offline --locked --manifest-path .\src-tauri\Cargo.toml
.\.venv\Scripts\python.exe .\scripts\desktop_smoke.py
```

Frontend tests exercise native reply evidence, safe text rendering, explicit draft inclusion, serialized autosaves, save failures, draft recovery, revision tokens, undo/redo, and keyboard behavior. The desktop smoke test uses synthetic data to check the protocol, single-instance lock, draft recovery, confirmation, revision conflicts, and CSV/JSON outputs. These do not replace inspection of native dialogs or a packaged distribution on a clean machine. See `docs/DESKTOP_MIGRATION.md` for exploratory checks.
