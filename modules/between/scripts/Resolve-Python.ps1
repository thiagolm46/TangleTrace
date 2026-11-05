param([string]$ProjectRoot, [string]$ResearchRoot, [string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
$candidates = @(
    $PythonPath,
    $env:DISCORD_ANNOTATOR_PYTHON,
    (Join-Path $ProjectRoot '.venv\Scripts\python.exe'),
    (Join-Path $ResearchRoot '.venv\Scripts\python.exe')
)
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        try { & $candidate -c 'import duckdb, pandas, pyarrow' 2>$null } catch { continue }
        if ($LASTEXITCODE -eq 0) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
}
throw 'Python with duckdb, pandas, and pyarrow was not found. Specify -PythonPath or prepare .venv as described in README.md.'
