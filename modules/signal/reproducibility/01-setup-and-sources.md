# 1. Environment and Source Snapshots

[Guide index](README.md) | [Next: servers](02-server-filtering.md)

## Environment

Use Python **3.12** (the declared supported range is `>=3.12,<3.13`) and
[uv](https://docs.astral.sh/uv/). The dependency versions are fixed by
[uv.lock](../uv.lock); do not update dependencies during a reproduction.

```powershell
uv sync --locked
uv run --locked python --version
git --no-pager rev-parse HEAD
uv --version
```

Record these versions and whether the worktree is dirty. No GPU or model
download is required. Extraction streams messages in batches of 50,000 by
default. Channel selection uses DuckDB with a default 2 GB memory limit,
two threads and temporary disk spill. This is not a guarantee of total
process-memory usage. Generic channel scoring loads the selected scope into
pandas; score one server at a time when memory is limited.

## New Run Layout

Choose a new run identifier each time. Do not reuse historical directories.

```powershell
$Run = "data\processed\reproduction\run_001"
$Raw = "data\raw\reproduction\snapshot_001"
if ((Test-Path $Run) -or (Test-Path $Raw)) {
    throw "Choose unused run and snapshot directories."
}
New-Item -ItemType Directory -Path $Run, $Raw | Out-Null
$ServerProfile = "configs\filtering\software.engineering.v2.json"
$Review = "configs\filtering\server_review.v1.csv"
$Exclusions = "configs\filtering\channel_exclusions.v1.txt"
git --no-pager rev-parse HEAD | Set-Content "$Run\repository_commit.txt"
uv --version | Set-Content "$Run\uv_version.txt"
uv run --locked python --version | Set-Content "$Run\python_version.txt"
```

The shared `$Run`, `$Raw`, `$ServerProfile`, `$Review` and `$Exclusions`
variables are used on subsequent pages. In a new shell, set them again.
The directories are ignored by Git. Archive them securely outside Git if a
long-term reproduction is needed; do not commit raw messages.

## Upstream Data

Source repository:
[SaisExperiments/Discord-Unveiled-Compressed](https://huggingface.co/datasets/SaisExperiments/Discord-Unveiled-Compressed).
The downloader uses these paths:

| Upstream path | Content |
| --- | --- |
| `server_metadata/servers_metadata.txt` | JSON array of server metadata despite the `.txt` extension |
| `dataset.zst` | Zstandard-compressed tar archive with per-server JSON-lines members |

Review the upstream access, licensing and redistribution terms before
downloading. The full compressed archive is approximately **118 GB**.
Budget additional space for extracted Parquet, retained Parquet and temporary
files; raw archive size is not the final storage requirement.

### Frozen snapshot route (recommended)

Select an immutable upstream **commit revision** using the dataset's revision
history, and record it. Substitute that actual revision below; a placeholder
or `main` is not a frozen reference.

```powershell
$Revision = "<upstream-commit-revision>"
if ($Revision -eq "<upstream-commit-revision>" -or $Revision -eq "main") {
    throw "Set an immutable upstream commit revision."
}
$Base = "https://huggingface.co/datasets/SaisExperiments/Discord-Unveiled-Compressed/resolve/$Revision"
$Revision | Set-Content "$Run\upstream_revision.txt"
curl.exe --fail --location --retry 5 `
  "$Base/server_metadata/servers_metadata.txt?download=true" `
  --output "$Raw\servers_metadata.txt"
if ($LASTEXITCODE -ne 0) { throw "Metadata download failed." }
curl.exe --fail --location --retry 5 `
  "$Base/dataset.zst?download=true" `
  --output "$Raw\dataset.zst"
if ($LASTEXITCODE -ne 0) { throw "Archive download failed." }
Get-FileHash "$Raw\servers_metadata.txt", "$Raw\dataset.zst" -Algorithm SHA256 |
  Export-Csv "$Run\source_hashes.csv" -NoTypeInformation
```

These are public upstream downloads, not uploads of local data. If access
requires authentication, follow upstream instructions without placing tokens
in scripts or Git.

The historical metadata SHA-256 was
`d3e4bdd63768dceb5ad54ffb4128a2581262937d8de1a198637f45496318721b`.
The original upstream commit revision is not preserved in the historical
scoring manifest; the hash identifies the metadata bytes, not the current
remote branch. Do not claim exact historical recovery without matching inputs.

### Current-upstream convenience route

For a new study, the built-in commands are:

```powershell
uv run --locked python -m discord_data download-metadata `
  --output-path "$Raw\servers_metadata.txt"
uv run --locked python -m discord_data download-dataset `
  --output-path "$Raw\dataset.zst"
```

They resolve upstream **`main`**, which can change. They also open the output
for writing: unlike derived filtering artifacts, download destinations are
not overwrite-protected. Use new paths, hash immediately, record the upstream
revision independently, and keep the downloaded snapshot.

Extraction can instead stream the remote archive without storing 118 GB.
This saves local archive storage, **not necessarily network traffic**: the
compressed tar stream is traversed sequentially. Use the local frozen route
when repeatable source bytes are required.
