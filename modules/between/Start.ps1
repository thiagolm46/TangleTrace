# Default desktop entry point; no application HTTP server.
[CmdletBinding()]
param(
    [string]$ResearchRoot = (Join-Path $PSScriptRoot '..\signal'),
    [string]$PythonPath = '',
    [string]$Workspace = '',
    [string]$Source = '',
    [switch]$Offline,
    [switch]$Diagnose
)
& (Join-Path $PSScriptRoot 'Start-Desktop.ps1') @PSBoundParameters
