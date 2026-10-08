param([ValidateSet('Prepare', 'Pilot', 'Validation', 'Final', 'Verify', 'All')][string]$Step = 'Prepare')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:TEMP = Join-Path (Get-Location) '.tools/stage4-tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP, 'data/processed/model_features_v1', 'data/processed/model_predictions_v1' | Out-Null
function Invoke-ModelJob {
    param([string]$Script, [string[]]$JobArgs = @())
    & docker compose -f docker/spark/compose.models.yaml run --rm spark "/workspace/src/models/$Script" @JobArgs
    if ($LASTEXITCODE -ne 0) { throw "Stage 4 job failed: $Script" }
}
function Write-Stage4Environment {
    $mlImage = docker image inspect bigdata-spark-ml:3.5.7-py311-np1264 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Spark ML image' }
    $engineVersion = docker version --format '{{.Server.Version}}'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read Docker server version' }
    [ordered]@{complete=$true; captured_at_utc=(Get-Date).ToUniversalTime().ToString('o');
        image_id=$mlImage[0].Id; repo_digests=$mlImage[0].RepoDigests; image_reported_bytes=$mlImage[0].Size;
        engine_version=$engineVersion; effective_cpu_limit=2; container_memory_limit_gib=4; driver_heap_gib=2;
        spark_local_mode='local[2]'; spark_version='3.5.7'; linux_python='3.11.17'; numpy_linux='1.26.4';
        temp_and_output_root=(Get-Location).Path; resource_measurement='snapshot only, not peak or cluster benchmark'
    } | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 'artifacts/metrics/stage4_environment.json'
}
if ($Step -in @('Prepare', 'All')) {
    & .\.venv\Scripts\python.exe -m src.models.preflight
    if ($LASTEXITCODE -ne 0) { throw 'Input preflight failed' }
    & .\.venv\Scripts\python.exe -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
    & docker build --pull=false -f docker/spark/Dockerfile.models -t bigdata-spark-ml:3.5.7-py311-np1264 docker/spark
    if ($LASTEXITCODE -ne 0) { throw 'Spark ML image build failed' }
    Write-Stage4Environment
    Invoke-ModelJob -Script 'spark_smoke.py'
    Invoke-ModelJob -Script 'check_features.py'
    if (-not (Test-Path 'artifacts/metrics/stage4_features.json')) {
        Invoke-ModelJob -Script 'features.py'
    } else {
        $featureReport = Get-Content 'artifacts/metrics/stage4_features.json' -Raw | ConvertFrom-Json
        if (-not $featureReport.complete) { throw 'Prior feature run incomplete; inspect before rerun' }
    }
}
if ($Step -in @('Pilot', 'All')) { Invoke-ModelJob -Script 'train.py' -JobArgs @('--mode', 'pilot') }
if ($Step -in @('Validation', 'All')) {
    foreach ($experiment in @('A_2024_only', 'B_add_2023')) {
        foreach ($depth in @(8, 12)) {
            foreach ($fold in @(0, 1, 2)) {
                Invoke-ModelJob -Script 'train.py' -JobArgs @('--mode', 'validation', '--experiment', $experiment, '--depth', "$depth", '--fold', "$fold")
            }
        }
    }
    & .\.venv\Scripts\python.exe -m src.models.choose_model
    if ($LASTEXITCODE -ne 0) { throw 'Model selection failed' }
}
if ($Step -in @('Final', 'All')) {
    Invoke-ModelJob -Script 'train.py' -JobArgs @('--mode', 'final')
}
if ($Step -in @('Verify', 'All')) {
    Invoke-ModelJob -Script 'check_saved_model.py'
    & .\.venv\Scripts\python.exe -m src.models.verify
    if ($LASTEXITCODE -ne 0) { throw 'Stage 4 acceptance failed' }
    $env:MPLCONFIGDIR = Join-Path (Get-Location) '.tools/stage4-tmp/matplotlib'
    & .\.venv\Scripts\python.exe -m src.models.report
    if ($LASTEXITCODE -ne 0) { throw 'Stage 4 report/figures failed' }
}
