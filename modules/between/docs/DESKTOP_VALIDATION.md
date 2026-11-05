# Desktop Verification Record · 0.3.0

These historical results predate the TangleTrace BETWEEN rename; the recorded
distribution name below identifies the build that was actually tested.

## Primer React Migration · 2026-11-04

The interface was replaced with React + TypeScript and official Primer React components. The Rust host and Python scientific rules remain in place; no database schema or research data migration was performed.

| Check performed | Result |
| --- | --- |
| `npm test` | Passed: 26 tests covering real Primer rendering, IPC shape, native evidence, safe text, drafts, queued writes, failures, navigation, revision conflicts, recovery, exports, and keyboard behavior |
| `npm run build` | Passed: strict TypeScript and production Vite assets |
| `cargo build --offline --locked --manifest-path .\src-tauri\Cargo.toml` | Passed with React assets embedded |
| `Start-Desktop.ps1 -Offline -Diagnose -Workspace <synthetic temporary folder>` | Passed: frontend build, Rust launch, Python configuration, and shutdown |
| `desktop_smoke.py` | Passed: real worker pipes, lock, draft recovery, confirmation, conflicts, and CSV/JSON export |
| `smoke_check.py` | Passed: scientific graph, reviews, history, isolation, recovery, and materializer; rerun after a transient OneDrive file-lock during temporary cleanup |
| Updated PowerShell files | Syntax checks passed |
| Browser checks with synthetic IPC | Passed at widths 1440, 1280, and 640: no horizontal overflow, responsive panes, native reply inspection without confirmation, explicit link addition and confirmation, conversation review, blocked premature validation, comparison table, and reveal through active filters |
| Primer themes | Light/dark rendering inspected; no external style or font requests required |

Browser verification used a test-only IPC stub injected by browser automation, not a production fallback or research database. Native Windows file dialogs, full interactive WebView2 behavior, the release packaging path, and operation on a clean machine were not revalidated for this frontend change. Run `Build-Desktop.ps1` to produce a new distribution; the historical packaged executable below does not include Primer React.

Known dependency/build notices: the production JavaScript bundle exceeds Vite's 500 kB advisory threshold. `npm audit` reports two low-severity entries involving Primer React's transitive `deepmerge` dependency ([GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4)); npm currently reports no available fix. No unsafe dependency overrides were added.

## Historical Desktop Validation · 2026-10-22

Refactoring was performed in the `annotation-tool` directory on 2026-10-22. No new source-code ZIP was created.

## Produced Distribution

`desktop-build/desktop-20261022-161106/discord-se-desktop.exe`, with the processor and its dependencies in `worker/`. Windows x64 distribution, approximately 196 MiB. The host bundles the interface; the worker bundles Python 3.12 and the data libraries. The build used PyInstaller 6.22.3 without installing packages in the research environment.

## Observed Results

| Check performed | Result |
| --- | --- |
| `cargo check --offline` | Passed |
| `cargo build --offline --locked` | Passed |
| Rust release build | Passed |
| Python compilation and JavaScript/PowerShell syntax | Passed |
| `interface_smoke.cjs` | Passed: replies and decisions remain separate |
| `smoke_check.py` | Passed: graph, history, review, isolation, recovery, and materializer |
| `desktop_smoke.py` with development Python | Passed |
| `desktop_smoke.py --worker <packaged executable>` | Passed when run outside the source directory |
| Packaged Rust host with `--diagnose` | Passed: version 0.3.0 and protocol 1 |

The packaged worker was exercised with a synthetic import, second-process blocking on the same workspace, recoverable errors, saved draft, shutdown, resume, confirmation, revision conflict, and export. `summary.csv`, `summary.json`, Parquet files, and a manifest were produced by the bundled runtime.

The upstream materializer before English diagnostic localization had SHA-256 `63a3e5ae1fb6ee2c19cd7c64cc5f419b5f21356a1ec6b4295314d4b139631717`. The bundled copy changes only validation messages; derivation and export logic are unchanged. Its current SHA-256 is `97ED1AB4CE885F6618C436BE78CB27BE160BA2AFAA1F26E4879E60AF581B770F`.

## Verification Limitations

The native window, Windows file dialogs, and responsive layout did not receive automated visual inspection in this refactoring. Operation on another clean machine was also not verified. Use the checklist in `DESKTOP_MIGRATION.md` for exploratory testing.

Tests used separate synthetic workspaces. The research annotation database and source files were not modified. Historical real-data import counts documented in version 0.2 were not rerun in this phase.
