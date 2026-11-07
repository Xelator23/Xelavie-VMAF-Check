# Native Windows launcher. uv must already be installed if Python is missing.
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
$uv = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Error 'Python 3.10+ oder bereits installiertes uv erforderlich. uv wird nicht automatisch installiert.'
    exit 1
}
Write-Host 'Python fehlt. Verwende vorhandenes uv fuer Python 3.12 ...'
& $uv.Source run --no-config --no-project --python 3.12 $program @scriptArguments
exit $LASTEXITCODE
