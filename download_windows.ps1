param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$Destination
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
    $uri = [Uri]$Url
    if ($uri.Scheme -ne 'https') { throw 'Nur HTTPS-Downloads sind erlaubt.' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    # Windows/.NET performs its normal certificate and hostname validation.
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $Destination -TimeoutSec 600 -UserAgent 'local-vmaf-check/5.1'
    exit 0
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
