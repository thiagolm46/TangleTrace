# Reproducibility Protocol

This document describes how to prepare, run, and verify TangleTrace BETWEEN (`tangletrace-between`) from source. Corpus preparation and sampling are provided separately by TangleTrace SIGNAL (`tangletrace-signal`). This protocol distinguishes repeatable application behavior from bit-for-bit reproducible builds: the current Python dependency files specify version ranges, and the Windows WebView2 runtime is supplied by the host machine.

## Supported environment

- Windows 10 or later, x64.
- Python 3.12 or later.
- Stable Rust toolchain, MSVC C++ build tools, and Windows SDK for source builds.
- Microsoft Edge WebView2 Runtime.
- Node.js 22.12 or later (Node 24 LTS recommended) and npm for the React interface build and tests.
- Source data in the documented CSV/Parquet schema; the synthetic demonstration requires no research data.

Python dependencies are declared in `requirements.txt` and `requirements-desktop.txt`. Rust dependencies and versions are recorded in `src-tauri/Cargo.lock`; frontend dependencies are pinned in `package-lock.json` and restored with `npm ci`. Python constraints currently use compatible version ranges rather than a complete hash-locked environment. Record the resolved versions when producing an evaluation package.

## Prepare a clean environment

Run these commands from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
node --version
npm ci
rustc --version
cargo --version
```

For a desktop distribution, also install the build dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
```

Dependency installation may access package indexes. After installation, the desktop annotation workflow runs locally and can be used without network access.

## Run the application

Start the desktop application from source:

```powershell
.\Start-Desktop.ps1 -PythonPath '.\.venv\Scripts\python.exe'
```

Open the synthetic demonstration from the welcome screen to exercise the workflow without research data. For a real sample, provide the existing sampled data directory or supported CSV/Parquet input. Import does not perform sampling or modify source files.

## Verification

Run the focused checks from the repository root:

```powershell
npm test
npm run build
cargo check --offline --locked --manifest-path .\src-tauri\Cargo.toml
.\.venv\Scripts\python.exe .\scripts\smoke_check.py
.\.venv\Scripts\python.exe .\scripts\desktop_smoke.py
```

The desktop smoke test uses temporary synthetic inputs and a temporary workspace. It checks worker protocol handling, single-instance locking, draft persistence and recovery, confirmation, optimistic revision conflicts, and CSV/JSON exports. It does not read or modify research data.

To build the distributable desktop application:

```powershell
.\Build-Desktop.ps1 -PythonPath '.\.venv\Scripts\python.exe'
```

The output contains the desktop executable and its adjacent `worker` directory. Run the packaged worker smoke check described by `python .\scripts\desktop_smoke.py --help` when validating a release build.

## Verify an exported artifact

Each export is written to a new session-specific directory and contains `manifest.json`, `summary.csv`, `summary.json`, human annotation tables, derived graph tables, and review records. The manifest records the export status, revision, provenance, and available input/source hashes. Preserve the manifest with the exported data when sharing or analyzing results.

Counts describe the imported sample and confirmed session snapshot. They are not population estimates. Native platform replies and human-confirmed annotation links are represented separately. Drafts are excluded from labels.

## Record an evaluation environment

For each submitted evaluation, record:

- Source revision or source archive SHA-256.
- Windows edition and architecture.
- Python, pip, Node.js, Rust, Cargo, MSVC, and WebView2 versions.
- Resolved Python dependencies (for example, `python -m pip freeze`).
- Exact verification commands and their exit status.
- Input archive identity and hashes, subject to data-sharing restrictions.
- Export manifest and whether the session was individual or adjudicated.

## Known reproducibility limits

- Python requirements are range-based, not hash-locked; dependency resolution may change over time.
- WebView2 rendering depends on the installed Windows runtime.
- The current build is not guaranteed to be bit-for-bit reproducible or digitally signed.
- Automated smoke tests do not replace visual checks of the native window, Windows file dialogs, scaling, and accessibility behavior.
- Research inputs are not included. The demonstration is synthetic and cannot reproduce findings from a private or separately distributed corpus.