param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$SkipConsumer
)

$ErrorActionPreference = "Stop"

$providerJar = Join-Path $Root "edc-runtime\transfer\transfer-03-consumer-pull\provider-proxy-data-plane\build\libs\connector.jar"
$consumerJar = Join-Path $Root "edc-runtime\transfer\transfer-00-prerequisites\connector\build\libs\connector.jar"
$providerConfig = Join-Path $Root "provider\config"
$consumerConfig = Join-Path $Root "consumer\config\consumer.properties"
$logDirectory = Join-Path $Root "runtime-logs"
$federationServerConfig = Join-Path $Root "consumer\config\federation-server.properties"
if (-not (Test-Path -LiteralPath $providerJar)) {
    throw "Provider JAR not found: $providerJar"
}
if (-not $SkipConsumer -and -not (Test-Path -LiteralPath $consumerJar)) {
    throw "Consumer JAR not found: $consumerJar"
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Start-Connector {
    param(
        [string]$Name,
        [string]$Jar,
        [string]$Config
    )

    $stdout = Join-Path $logDirectory "$Name.out.log"
    $stderr = Join-Path $logDirectory "$Name.err.log"
    $process = Start-Process -FilePath "java" `
        -ArgumentList @("-Dedc.fs.config=$Config", "-jar", $Jar) `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    Write-Output "$Name started with PID $($process.Id)"
}

Start-Connector -Name "factory-1" `
    -Jar $providerJar `
    -Config (Join-Path $providerConfig "provider.properties")
Start-Connector -Name "factory-2" `
    -Jar $providerJar `
    -Config (Join-Path $providerConfig "factory-2.properties")
Start-Connector -Name "factory-3" `
    -Jar $providerJar `
    -Config (Join-Path $providerConfig "factory-3.properties")

if (-not $SkipConsumer) {
    Start-Connector -Name "consumer" -Jar $consumerJar -Config $consumerConfig
}

Start-Connector -Name "federation-server" `
    -Jar $consumerJar `
    -Config $federationServerConfig