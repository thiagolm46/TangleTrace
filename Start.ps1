[CmdletBinding()]
param(
    [string]$ResearchRoot = (Join-Path $PSScriptRoot 'modules\signal'),
    [string]$PythonPath = '',
    [string]$Workspace = '',
    [string]$Source = '',
    [switch]$Offline,
    [switch]$Diagnose
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'modules\between\Start-Desktop.ps1') @PSBoundParameters