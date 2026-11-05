[CmdletBinding()]
param(
    [string]$ResearchRoot = (Join-Path $PSScriptRoot '..\signal'),
    [string]$PythonPath = '',
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
$pythonExe = & (Join-Path $PSScriptRoot 'scripts\Resolve-Python.ps1') -ProjectRoot $PSScriptRoot -ResearchRoot $ResearchRoot -PythonPath $PythonPath
& $pythonExe -c 'import PyInstaller' 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Install PyInstaller in the build Python environment (see requirements-desktop.txt). Packages are not installed automatically.' }
& (Join-Path $PSScriptRoot 'scripts\Build-Frontend.ps1')
$cargoArgs = @('build', '--release', '--locked', '--manifest-path', (Join-Path $PSScriptRoot 'src-tauri\Cargo.toml'))
if ($Offline) { $cargoArgs += '--offline' }
& cargo @cargoArgs
if ($LASTEXITCODE -ne 0) { throw 'Rust build failed.' }
# Each build uses a new folder and does not overwrite a running application.
$buildName = 'desktop-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$outputRoot = Join-Path $PSScriptRoot (Join-Path 'desktop-build' $buildName)
$buildWork = Join-Path $PSScriptRoot (Join-Path 'src-tauri\target\pyinstaller' $buildName)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
Set-Content -LiteralPath (Join-Path $outputRoot 'INCOMPLETE.txt') -Value 'Build incomplete. Do not use as a distribution.' -Encoding UTF8
Write-Host 'Packaging the local processor and its data libraries...'
# Use the Win32 prefix to support long names in OneDrive/project directories.
$freezeDist = if ($outputRoot.StartsWith('\\')) { '\\?\UNC\' + $outputRoot.Substring(2) } else { '\\?\' + $outputRoot }
$freezeArgs = @('-m', 'PyInstaller', '--noconfirm', '--log-level', 'WARN', '--onedir', '--name', 'worker',
    '--paths', $PSScriptRoot, '--distpath', $freezeDist, '--workpath', $buildWork, '--specpath', $buildWork,
    '--collect-all', 'duckdb', '--collect-binaries', 'pyarrow', '--hidden-import', 'pyarrow.parquet',
    '--exclude-module', 'pandas.tests', '--exclude-module', 'pyarrow.tests', '--exclude-module', 'numpy.tests',
    '--exclude-module', 'pytest', '--exclude-module', 'matplotlib', '--exclude-module', 'scipy',
    '--exclude-module', 'sklearn', '--exclude-module', 'IPython', '--exclude-module', 'numba',
    '--add-data', ((Join-Path $PSScriptRoot 'app\vendor\CODEBOOK.md') + ';app/vendor'),
    '--add-data', ((Join-Path $PSScriptRoot 'app\vendor\annotation_bundle.py') + ';app/vendor'),
    (Join-Path $PSScriptRoot 'scripts\worker_entry.py'))
& $pythonExe @freezeArgs
if ($LASTEXITCODE -ne 0) { throw 'Processor packaging failed. Do not distribute the partial folder.' }
$resolvedOutput = (Resolve-Path -LiteralPath $outputRoot).Path
Rename-Item -LiteralPath (Join-Path $resolvedOutput 'worker\worker.exe') -NewName 'discord-annotation-worker.exe'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'src-tauri\target\release\tangletrace-between.exe') -Destination $resolvedOutput
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'docs\USER_GUIDE.md') -Destination $resolvedOutput
Remove-Item -LiteralPath (Join-Path $resolvedOutput 'INCOMPLETE.txt')
Write-Host "Complete application built at $resolvedOutput"
Write-Host 'Open tangletrace-between.exe. Keep the worker folder beside the executable.'
