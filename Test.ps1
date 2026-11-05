[CmdletBinding()]
param([string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
$betweenRoot = Join-Path $PSScriptRoot 'modules\between'
$signalRoot = Join-Path $PSScriptRoot 'modules\signal'
$pythonExe = & (Join-Path $betweenRoot 'scripts\Resolve-Python.ps1') -ProjectRoot $betweenRoot -ResearchRoot $signalRoot -PythonPath $PythonPath
Push-Location $signalRoot
try {
    & $pythonExe -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw 'SIGNAL tests failed.' }
} finally {
    Pop-Location
}
Push-Location $betweenRoot
try {
    & $pythonExe scripts\smoke_check.py
    if ($LASTEXITCODE -ne 0) { throw 'BETWEEN scientific smoke check failed.' }
    & $pythonExe scripts\desktop_smoke.py
    if ($LASTEXITCODE -ne 0) { throw 'BETWEEN desktop protocol smoke check failed.' }
    & npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw 'BETWEEN frontend tests failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'BETWEEN frontend build failed.' }
} finally {
    Pop-Location
}
Write-Host 'TangleTrace module checks passed.'