# Native Windows bootstrap. All downloaded runtime files stay in a unique temp directory.
$scriptArguments = @($args)
$ErrorActionPreference = 'Stop'
$program = Join-Path $PSScriptRoot 'vmaf_launcher.py'
foreach ($candidate in @('python', 'python3', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    $prefix = @()
    if ($candidate -eq 'py') { $prefix = @('-3') }
    try {
        & $cmd.Source @prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -ne 0) { continue }
        & $cmd.Source @prefix $program @scriptArguments
        exit $LASTEXITCODE
    } catch { Write-Verbose "Python candidate unavailable: $candidate" }
}
if ($scriptArguments -contains '--no-download') {
    Write-Error 'Python 3.10+ fehlt; --no-download verhindert den Bootstrap.'
    exit 1
}
$tempParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$bootstrapDir = Join-Path $tempParent ('vmaf-bootstrap-' + [guid]::NewGuid().ToString('N'))
$exitCode = 1
try {
    New-Item -ItemType Directory -Path $bootstrapDir | Out-Null
    $machine = $env:PROCESSOR_ARCHITEW6432
    if (-not $machine) { $machine = $env:PROCESSOR_ARCHITECTURE }
    switch ($machine) {
        'AMD64' { $arch = 'x86_64'; $expected = '0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021' }
        'ARM64' { $arch = 'aarch64'; $expected = '505d9e65e7692bac3ddf98c66754aa26c5050c409c184af30a881a0a72cc85e3' }
        default { throw "Nicht unterstuetzte Windows-Architektur: $machine" }
    }
    $asset = "uv-$arch-pc-windows-msvc.zip"
    $archive = Join-Path $bootstrapDir 'uv.zip'
    Write-Host 'Python fehlt. Lade geprueften temporaeren uv/Python-Bootstrap ...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/astral-sh/uv/releases/download/0.13.7/$asset" -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw 'SHA256 des uv-Downloads stimmt nicht.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $bootstrapDir 'uv')
    $uv = @(Get-ChildItem -LiteralPath (Join-Path $bootstrapDir 'uv') -Filter uv.exe -Recurse)
    if ($uv.Count -ne 1) { throw 'uv.exe nicht eindeutig gefunden.' }
    $env:UV_CACHE_DIR = Join-Path $bootstrapDir 'cache'
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $bootstrapDir 'python'
    $env:UV_PYTHON_BIN_DIR = Join-Path $bootstrapDir 'bin'
    $env:UV_NO_CONFIG = '1'
    & $uv[0].FullName run --no-project --python 3.12 $program @scriptArguments
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host ('FEHLER: ' + $_.Exception.Message) -ForegroundColor Red
} finally {
    $resolved = [IO.Path]::GetFullPath($bootstrapDir)
    if ($resolved.StartsWith($tempParent, [StringComparison]::OrdinalIgnoreCase) -and
        [IO.Path]::GetFileName($resolved) -match '^vmaf-bootstrap-[0-9a-f]{32}$') {
        if (Test-Path -LiteralPath $resolved) {
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}
exit $exitCode
