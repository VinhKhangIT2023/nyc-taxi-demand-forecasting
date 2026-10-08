param([ValidateSet('Prepare','Geometry','Load','Verify','App')][string]$Step='App')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$taskPython=Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Tạo .venv và cài requirements.txt trước.' }
if ($Step -eq 'App') {
    & $taskPython -m streamlit run src/dashboard/app.py
} else {
    & $taskPython -m src.dashboard.prepare $Step.ToLower()
    if ($LASTEXITCODE -ne 0) { throw "Bước $Step thất bại; xem thông báo phía trên." }
    if ($Step -eq 'Verify') { & $taskPython -m src.dashboard.verify }
}
if ($LASTEXITCODE -ne 0) { throw "Bước $Step thất bại; xem thông báo phía trên." }
