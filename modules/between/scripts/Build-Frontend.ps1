[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Node.js 22.12 or later and npm are required to build the React interface. See README.md.'
}
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'node_modules\.package-lock.json'))) {
    throw 'Frontend dependencies are missing. Run npm ci in the project directory. Packages are not installed automatically.'
}
Push-Location $projectRoot
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'React frontend build failed. The desktop host was not built.' }
} finally {
    Pop-Location
}
