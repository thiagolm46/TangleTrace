[CmdletBinding()]
param(
    [string]$Destination = $PSScriptRoot,
    [switch]$ReplaceExisting
)
$ErrorActionPreference = 'Stop'
$sourceRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$destinationRoot = [System.IO.Path]::GetFullPath($Destination)
if ($sourceRoot.TrimEnd('\') -eq $destinationRoot.TrimEnd('\')) {
    Write-Host 'The application is already at the destination. Run start.cmd.'
    exit 0
}
$allowedTopLevel = @('app','docs','scripts','src','src-tauri','index.html','package.json','package-lock.json','tsconfig.json','vite.config.ts','README.md','requirements.txt','requirements-desktop.txt','pyproject.toml','Start.ps1','Start-Desktop.ps1','Build-Desktop.ps1','start.cmd','start-desktop.cmd','Install.ps1','Update.ps1','update.cmd','.gitignore')
function Get-ImplementationFiles([string]$directory) {
    foreach ($entry in Get-ChildItem -LiteralPath $directory -Force) {
        if ($entry.PSIsContainer) {
            if ($entry.Name -notin @('__pycache__','.venv','workspace','target','gen','.git','desktop-build')) { Get-ImplementationFiles $entry.FullName }
        } else { $entry }
    }
}
$files = foreach ($name in $allowedTopLevel) {
    $itemPath = Join-Path $sourceRoot $name
    if (Test-Path -LiteralPath $itemPath -PathType Container) { Get-ImplementationFiles $itemPath }
    elseif (Test-Path -LiteralPath $itemPath -PathType Leaf) { Get-Item -LiteralPath $itemPath }
}
$conflicts = @()
foreach ($file in $files) {
    $relative = $file.FullName.Substring($sourceRoot.Length).TrimStart('\')
    $target = Join-Path $destinationRoot $relative
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash) { $conflicts += $relative }
    }
}
if ($conflicts.Count -and -not $ReplaceExisting) {
    throw ('Implementation files already exist with different contents: ' + ($conflicts -join ', ') + '. Review them or use -ReplaceExisting to back them up before replacement.')
}
New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
$backupRoot = Join-Path $destinationRoot ('installation-backups\' + (Get-Date -Format 'yyyyMMddTHHmmssfff'))
foreach ($file in $files) {
    $relative = $file.FullName.Substring($sourceRoot.Length).TrimStart('\')
    $target = Join-Path $destinationRoot $relative
    if ($conflicts -contains $relative) {
        $backupTarget = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backupTarget) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backupTarget
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $target -Force
}
Write-Host "Implementation installed at $destinationRoot"
Write-Host 'Run start.cmd to launch the desktop app. Scientific documentation and research data were preserved.'
