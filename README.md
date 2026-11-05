# TangleTrace

**An Auditable Workbench for Discord Conversation Annotation**

TangleTrace is a modular monorepo containing the corpus preparation pipeline
and the local reply-link annotation desktop application.

| Module | Location | Responsibility |
| --- | --- | --- |
| SIGNAL | [modules/signal](modules/signal/README.md) | Data acquisition, filtering, population characterization, sampling and audits |
| BETWEEN | [modules/between](modules/between/README.md) | Import, human annotation, review, adjudication and export |

Both modules retain their own packaging, dependencies, tests and documentation.
The Python distributions remain `tangletrace-signal` and `tangletrace-between`.
Existing Python imports, CLI entry points and artifact formats are unchanged.
This root is not a third Python package: run module-specific commands from
the corresponding module directory.

## Setup

SIGNAL requires Python 3.12 and uv. BETWEEN also requires Node.js 22.12 or
later, npm, stable Rust, the Windows C++ build tools/SDK and WebView2.
See each module's README for the full prerequisites.

From the repository root:

```powershell
Push-Location modules\signal
uv sync --locked
uv run --locked python -m discord_filtering --help
Pop-Location

Push-Location modules\between
npm ci
Pop-Location

.\Start.ps1
```

The desktop launcher can use SIGNAL's Python environment, which contains the
shared data dependencies. Alternatively, create BETWEEN's own `.venv` and
install its `requirements.txt`. Both environments remain local and unversioned.
Distribution builds additionally require BETWEEN's `requirements-desktop.txt`.

`start.cmd` launches the same desktop application. The root launcher forwards
the existing arguments without changing the active annotation workspace:

```powershell
.\Start.ps1 -Source 'C:\datasets\sample' -Workspace 'C:\annotations\workspace'
.\Start.ps1 -ResearchRoot 'C:\another-signal' -PythonPath 'C:\env\Scripts\python.exe'
```

Without `-ResearchRoot`, BETWEEN uses `modules/signal`. Without `-Source`, it
checks that module's `data/processed/disentanglement/sampling_pilot_v1`.
Annotation workspaces retain the desktop application's existing selection
and recovery rules; no previous database is moved or merged automatically.

## Module Handoff

SIGNAL produces sampled windows. BETWEEN imports a sample directory containing
`sampled_messages.parquet` and `selected_windows.csv`, or the windows CSV.
The canonical annotation bundle is a separate interchange output, not the
desktop's direct import format. See the
[preparation guide](modules/signal/reproducibility/05-validation-and-preparation.md)
and [artifact specification](modules/between/docs/ARTIFACT_SPEC.md).

## Verification

After installing dependencies:

```powershell
.\Test.ps1
```

This runs SIGNAL's pytest suite, BETWEEN's Python smoke checks, frontend tests
and frontend production build. Use `-PythonPath` to select a prepared Python
environment explicitly. The native host remains a separate verification gate:

```powershell
cargo check --locked --manifest-path modules\between\src-tauri\Cargo.toml
```

Native dialogs and a packaged distribution still require manual desktop checks.
To build a distribution, run `modules/between/Build-Desktop.ps1` with the
arguments described in BETWEEN's README.

## Data And Migration

Research data, virtual environments, node_modules, build outputs and annotation
workspaces are not distributed in this repository. Versionable scientific
configurations, decisions, documentation and provenance records are included.
Historical provenance paths are preserved, not rewritten as if the original
runs had occurred in this layout.

See [the migration record](docs/MIGRATION.md) for the copy policy, exclusions
and instructions for using existing local data. The original project
directories were not changed or deleted.