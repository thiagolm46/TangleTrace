[CmdletBinding()]
param([string]$Destination = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$Destination = [System.IO.Path]::GetFullPath($Destination)
if ((Test-Path -LiteralPath $Destination) -and -not (Test-Path -LiteralPath (Join-Path $Destination 'workspace\annotations.sqlite3'))) {
    $withAnnotations = @(Get-ChildItem -LiteralPath $Destination -Directory | Where-Object {
        ($_.Name -like 'Discord_SE_Annotation_Tool*' -or
         $_.Name -like 'tangletrace-between*' -or
         $_.Name -like 'TangleTrace_BETWEEN*') -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'Start-Desktop.ps1')) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'workspace\annotations.sqlite3'))
    })
    if ($withAnnotations.Count -eq 1) { $Destination = $withAnnotations[0].FullName }
    elseif ($withAnnotations.Count -gt 1) { throw 'Multiple desktop installations contain annotations. Run Update.ps1 -Destination with the exact active installation path.' }
}
Write-Host 'Updating TangleTrace BETWEEN to version 0.3.0.'
Write-Host "Selected installation: $Destination"
Write-Host 'Close the desktop app before running this updater. Reopen start.cmd when it finishes.'
& (Join-Path $PSScriptRoot 'Install.ps1') -Destination $Destination -ReplaceExisting
Write-Host 'Update complete. The annotation database in workspace was not replaced.'
Write-Host ('Launch the desktop app: ' + (Join-Path $Destination 'start-desktop.cmd'))
Write-Host 'In My files, select this installation workspace to resume annotation.'
