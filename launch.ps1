param([switch]$Check)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = $null
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $localPython) { $taskPython = $localPython }
elseif (Test-Path -LiteralPath $bundledPython) { $taskPython = $bundledPython }
else {
    $candidate = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($candidate) { $taskPython = (& $candidate.Source -3 -c 'import sys; print(sys.executable)' | Select-Object -Last 1) }
    if (-not $taskPython) {
        $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.Source -notmatch 'WindowsApps') { $taskPython = $candidate.Source }
    }
}
if (-not $taskPython) {
    Write-Host 'Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/ and run again.'
    Read-Host 'Press Enter to close'; exit 1
}
& $taskPython -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PIL') else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Preparing local dependencies...'
    & $taskPython -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
    $taskPython = $localPython
    & $taskPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the network and retry.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'vendor\imageio_ffmpeg'))) {
    & $taskPython -m pip install --target (Join-Path $PSScriptRoot 'vendor') imageio-ffmpeg==0.6.0
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg installation failed.' }
}
if ($Check) { Write-Host ('READY: ' + $taskPython); exit 0 }
$statusFile = Join-Path $PSScriptRoot 'data\server.json'
if (Test-Path -LiteralPath $statusFile) {
    try {
        $status = Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json
        $response = Invoke-RestMethod -Uri ($status.url + '/api/config') -TimeoutSec 2
        if ($response.root -eq $PSScriptRoot) { Start-Process $status.url; exit 0 }
    } catch { }
}
Write-Host 'Keep this window open while editing. Press Ctrl+C to stop the studio.'
& $taskPython (Join-Path $PSScriptRoot 'app.py')
if ($LASTEXITCODE -ne 0) { Read-Host 'The studio stopped. Press Enter to close' }
