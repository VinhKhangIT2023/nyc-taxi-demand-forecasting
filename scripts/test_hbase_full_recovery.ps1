# Run from the project root in PowerShell. Full dataset offline backup into a fresh, isolated volume. Source is restarted in finally.
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $taskRoot
$taskImage = 'dajobe/hbase@sha256:daa36a6d90b118ced866b6c76fcd918e7da73302b0e4971f506f0f61f645a9fe'
$taskCompose = 'docker/hbase/compose.yaml'
$taskBackupDir = Join-Path $taskRoot '.tools\hbase-backups'
$taskArchive = Join-Path $taskBackupDir 'stage3-full.tar'
$taskRestoreVolume = 'bigdata-hbase-full-restore_hbase_data'
function Invoke-DockerChecked {
    param([string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker failed: $($Arguments -join ' ')" }
}
function Invoke-PythonChecked {
    param([string[]]$Arguments)
    & .\.venv\Scripts\python.exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Python verification failed' }
}
if (Test-Path -LiteralPath $taskArchive) { throw 'Archive exists; preserve evidence and use a separately reviewed run name.' }
$taskVolumes = @(Invoke-DockerChecked -Arguments @('volume','ls','--format','{{.Name}}'))
if ($taskRestoreVolume -in $taskVolumes) { throw 'Restore volume already exists; refusing to overwrite.' }
$taskId = Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase','-f',$taskCompose,'ps','-q','hbase')
if (-not $taskId) { throw 'Start the managed HBase trial first.' }
$taskBefore = (Invoke-DockerChecked -Arguments @('inspect',$taskId) | ConvertFrom-Json)[0]
$taskSourceVolume = @($taskBefore.Mounts | Where-Object { $_.Destination -eq '/data' })[0].Name
if ($taskSourceVolume -ne 'bigdata-hbase_hbase_data') { throw 'Unexpected source volume' }
New-Item -ItemType Directory -Path $taskBackupDir -Force | Out-Null
$taskVerification = Get-Content artifacts/metrics/hbase_full_verify_pass2.json -Raw | ConvertFrom-Json
if (-not $taskVerification.complete -or $taskVerification.rows -ne 6917952) { throw 'Full verification required' }
try {
    Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase','-f',$taskCompose,'stop','hbase')
    $taskStopped = (Invoke-DockerChecked -Arguments @('inspect',$taskId) | ConvertFrom-Json)[0]
    if ($taskStopped.State.Running -or $taskStopped.State.ExitCode -ne 0) { throw 'Clean shutdown required before backup' }
    Invoke-DockerChecked -Arguments @('run','--rm','--network','none','--entrypoint','tar',
        '--mount',"type=volume,source=$taskSourceVolume,target=/source,readonly",
        '--mount',"type=bind,source=$taskBackupDir,target=/backup",$taskImage,
        '-cpf','/backup/stage3-full.tar','-C','/source','.')
    $taskHash = (Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash
} finally {
    Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase','-f',$taskCompose,'start','hbase')
}
$taskOldPort = $env:HBASE_THRIFT_PORT
$taskOldUI = $env:HBASE_UI_PORT
try {
    $env:HBASE_THRIFT_PORT = '19092'
    $env:HBASE_UI_PORT = '16013'
    Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase-full-restore','-f',$taskCompose,'create','hbase')
    $taskRestoredId = Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase-full-restore','-f',$taskCompose,'ps','-a','-q','hbase')
    if ($taskRestoredId -eq $taskId) { throw 'Expected a different container' }
    $taskContents = Invoke-DockerChecked -Arguments @('run','--rm','--network','none','--entrypoint','find',
        '--mount',"type=volume,source=$taskRestoreVolume,target=/restore",$taskImage,'/restore','-mindepth','1','-print','-quit')
    if ($taskContents) { throw 'Restore destination is not empty' }
    if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash -ne $taskHash) { throw 'Archive changed' }
    Invoke-DockerChecked -Arguments @('run','--rm','--network','none','--entrypoint','tar',
        '--mount',"type=volume,source=$taskRestoreVolume,target=/restore",
        '--mount',"type=bind,source=$taskBackupDir,target=/backup,readonly",$taskImage,
        '-xpf','/backup/stage3-full.tar','-C','/restore')
    Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase-full-restore','-f',$taskCompose,'start','hbase')
    $taskDeadline = (Get-Date).AddSeconds(90)
    do {
        $taskState = (Invoke-DockerChecked -Arguments @('inspect',$taskRestoredId) | ConvertFrom-Json)[0].State
        if ($taskState.Health.Status -eq 'healthy') { break }
        if (-not $taskState.Running -or (Get-Date) -gt $taskDeadline) { throw 'Restored HBase did not become healthy' }
        Start-Sleep -Seconds 3
    } while ($true)
    Invoke-PythonChecked -Arguments @('-m','src.storage.verify_hbase_full','--port','19092',
        '--report','artifacts/metrics/hbase_full_after_restore.json','--compare','artifacts/metrics/hbase_full_verify_pass2.json')
    Invoke-PythonChecked -Arguments @('-m','src.storage.inspect_hbase_trial','--port','19092','--report','artifacts/metrics/hbase_full_restored_trial_readback.json')
    [ordered]@{ complete=$true; source_container=$taskId; restored_container=$taskRestoredId;
        source_volume=$taskSourceVolume; restored_volume=$taskRestoreVolume;
        clean_stop_exit_code=$taskStopped.State.ExitCode; archive='.tools/hbase-backups/stage3-full.tar';
        archive_sha256=$taskHash; image=$taskImage;
        scope='Offline backup of managed full dataset, restored into new container and volume; original hbase-demo unchanged.'
    } | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 artifacts/metrics/hbase_full_recovery.json
    # Keep recovery artifacts, but avoid leaving an unnecessary extra server using RAM.
    Invoke-DockerChecked -Arguments @('compose','-p','bigdata-hbase-full-restore','-f',$taskCompose,'stop','hbase')
} finally {
    $env:HBASE_THRIFT_PORT = $taskOldPort
    $env:HBASE_UI_PORT = $taskOldUI
}

