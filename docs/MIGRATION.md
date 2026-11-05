# Unified Repository Migration

Date: 2026-11-05.

## Layout And Copy Policy

| Original local directory | Unified module | Files copied before integration edits |
| --- | --- | --- |
| Annotation Tool | modules/between | 68 |
| Toxicity-OSS | modules/signal | 72 |

The initial copy used each original repository's current tracked files plus
untracked, non-ignored files (`git ls-files --cached --others --exclude-standard`).
It therefore captured working-tree contents rather than only the last commit.
All 140 copied files were checked against their originals with SHA-256 before
integration changes. Module file counts also matched the source inventory.

The original directories were left intact. Their `.git` directories were not
copied or nested inside this repository. This is a new repository snapshot,
not a merge of the two Git histories. No remote or initial commit is configured
automatically. The paper outside these two projects is outside this migration.

## Integration Changes

- BETWEEN's Start, Start-Desktop and Build-Desktop scripts default to sibling
  `../signal` rather than a user-specific historical path.
- BETWEEN's Install and Update scripts default to their own module directory,
  avoiding accidental writes to the original installation. An explicit
  `-Destination` still selects another installation.
- Both module READMEs now describe their location in the unified repository.
- Root documentation, launch scripts, ignore rules and a combined test runner
  provide a single repository entry point.

Python package names, imports, executable names, artifact schemas, module locks
and historical scientific manifests are preserved. Historical absolute paths
inside manifests identify original inputs; they are not portable runtime
defaults and were not rewritten.

## Excluded Local Artifacts

The original ignore policies exclude SIGNAL's `data/`, local DuckDB databases,
virtual environments and caches. BETWEEN additionally excludes `workspace/`,
SQLite databases, ZIPs, node_modules, frontend/Rust build outputs, generated
Tauri files and packaged desktop distributions. These artifacts were not
copied. Versionable annotations, configurations and provenance records remain
under SIGNAL's module.

Raw Discord messages and generated corpora must follow the upstream data terms.
An annotation database can contain personal or research data and must not be
committed. Existing local artifacts remain in the original directories.

## Reuse Existing Local Data

To use the original research environment and an existing sample without copying
the corpus, run from this repository root:

```powershell
.\Start.ps1 -ResearchRoot '..\Toxicity-OSS' `
  -Workspace '..\Annotation Tool\workspace'
```

Only select a workspace that actually contains the intended annotations and
close the old desktop application first. Otherwise omit `-Workspace` and use
the application's folder chooser. No databases are automatically merged.
Use `-Source` to choose any other existing sample directory.

For a fully independent local setup, regenerate research outputs from SIGNAL's
reproducibility instructions, or explicitly copy authorized data to
`modules/signal/data/`. Create fresh dependencies with `uv sync --locked` in
SIGNAL and `npm ci` in BETWEEN. Do not copy the old `.venv`: environments may
contain absolute paths and must be recreated after relocation.

## Validation Results

Validation ran from the new module locations on Windows using Python 3.12.13
from the original SIGNAL environment, without copying that environment.
Frontend dependencies were installed with `npm ci --offline --no-audit --no-fund`.

| Check | Result |
| --- | --- |
| Initial source copy | 140 files matched their originals by SHA-256 |
| PowerShell parsing and default module paths | Passed |
| SIGNAL pytest suite | 57 tests and 93 subtests passed |
| BETWEEN scientific smoke | Functional assertions completed; temporary-directory cleanup failed with WinError 32 on two runs |
| BETWEEN desktop protocol smoke | Passed, including lock, recovery, revision conflicts and export |
| BETWEEN frontend | 30 tests in four files passed |
| BETWEEN frontend production build | Passed; existing large-chunk warning remains |
| Native host `cargo check --offline --locked` | Passed |

The scientific smoke's cleanup failure is a Windows file-lock limitation in
the OneDrive location, also noted in the original desktop validation record.
Consequently the combined root `Test.ps1` did not complete successfully on this
machine; the remaining gates were run separately. No failure was suppressed or
treated as a passing test. Native window/dialog behavior and a fresh packaged
distribution were not manually verified as part of this migration.