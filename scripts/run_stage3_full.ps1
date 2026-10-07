# Continue after Spark full ETL has completed. Stop on any failed verification.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskSpark = Get-Content artifacts/metrics/spark_full.json -Raw | ConvertFrom-Json
if (-not $taskSpark.complete -or $taskSpark.months.Count -ne 36) { throw 'Complete Spark ETL first' }
foreach ($taskPass in @(1, 2)) {
    & docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/storage/spark_hbase_full.py --pass-number $taskPass
    if ($LASTEXITCODE -ne 0) { throw "Load pass $taskPass failed" }
    $taskArgs = @('-m', 'src.storage.verify_hbase_full', '--report', "artifacts/metrics/hbase_full_verify_pass$taskPass.json")
    if ($taskPass -eq 2) { $taskArgs += @('--compare', 'artifacts/metrics/hbase_full_verify_pass1.json') }
    & .\.venv\Scripts\python.exe @taskArgs
    if ($LASTEXITCODE -ne 0) { throw "Verification pass $taskPass failed" }
}
& $PSScriptRoot/test_hbase_full_recovery.ps1
if (-not (Get-Content artifacts/metrics/hbase_full_recovery.json -Raw | ConvertFrom-Json).complete) { throw 'Recovery verification incomplete' }
