[CmdletBinding()]
param(
    [string]$ResearchRoot = (Join-Path $PSScriptRoot '..\signal'),
    [string]$PythonPath = '',
    [string]$Workspace = '',
    [string]$Source = '',
    [switch]$Offline,
    [switch]$Diagnose
)
$ErrorActionPreference = 'Stop'
$pythonExe = & (Join-Path $PSScriptRoot 'scripts\Resolve-Python.ps1') -ProjectRoot $PSScriptRoot -ResearchRoot $ResearchRoot -PythonPath $PythonPath
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { throw 'Rust/Cargo is unavailable. See the prerequisites in README.md.' }
& (Join-Path $PSScriptRoot 'scripts\Build-Frontend.ps1')
if (-not $Source) {
    $pilotPath = Join-Path $ResearchRoot 'data\processed\disentanglement\sampling_pilot_v1'
    if (Test-Path -LiteralPath $pilotPath) { $Source = $pilotPath }
}
$previousEnv = @{}
foreach ($name in @('DISCORD_ANNOTATOR_PROJECT','DISCORD_ANNOTATOR_PYTHON','DISCORD_ANNOTATOR_WORKSPACE','DISCORD_ANNOTATOR_SOURCE')) {
    $previousEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
    $env:DISCORD_ANNOTATOR_PROJECT = $PSScriptRoot
    $env:DISCORD_ANNOTATOR_PYTHON = $pythonExe
    $env:DISCORD_ANNOTATOR_SOURCE = $Source
    # Without -Workspace, the desktop uses the last selected folder or LocalAppData.
    # Never silently select a demonstration database from the source directory.
    if ($Workspace) {
        $env:DISCORD_ANNOTATOR_WORKSPACE = [System.IO.Path]::GetFullPath($Workspace)
    } else {
        Remove-Item Env:DISCORD_ANNOTATOR_WORKSPACE -ErrorAction SilentlyContinue
    }
    $cargoArgs = @('build', '--locked', '--manifest-path', (Join-Path $PSScriptRoot 'src-tauri\Cargo.toml'))
    if ($Offline) { $cargoArgs += '--offline' }
    & cargo @cargoArgs
    if ($LASTEXITCODE -ne 0) { throw 'Rust build failed. See the message above.' }
    $desktopExe = Join-Path $PSScriptRoot 'src-tauri\target\debug\tangletrace-between.exe'
    if ($Diagnose) {
        if (-not $Workspace) { throw '-Diagnose requires -Workspace to point to a verification folder.' }
        & $desktopExe --diagnose
        if ($LASTEXITCODE -ne 0) { throw 'Local processor diagnostics failed.' }
    } else {
        Start-Process -FilePath $desktopExe -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    }
} finally {
    foreach ($name in $previousEnv.Keys) { [Environment]::SetEnvironmentVariable($name, $previousEnv[$name], 'Process') }
}
