param(
    [int]$StartRound = 1,
    [int]$EndRound = 5,
    [string]$ConsumerManagement = "http://localhost:59193/management/v3"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$WeightsDir = Join-Path $Root "weights"
$TraceDir = Join-Path $Root "traces"

for ($round = $StartRound; $round -le $EndRound; $round++) {
    $roundFile = "round_{0:D3}.json" -f $round
    Write-Output "=== Round $round ==="

    $missing = @()
    foreach ($factory in 1, 2, 3) {
        $path = Join-Path $WeightsDir "factory_$factory\$roundFile"
        if (-not (Test-Path -LiteralPath $path)) {
            $missing += $path
        }
    }

    if ($missing.Count -gt 0) {
        Write-Output "Round $round skipped, missing files:"
        $missing | ForEach-Object { Write-Output "  - $_" }
        continue
    }

    $summaryPath = Join-Path $TraceDir "round-$round-summary.json"
    python "$Root\scripts\run_federated_round.py" `
        --round $round `
        --consumer-management $ConsumerManagement `
        --trace-dir $TraceDir `
        --continue-on-error `
        --summary-path $summaryPath

    Write-Output ""
}
