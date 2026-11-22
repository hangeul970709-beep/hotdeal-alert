# 상품권 핫딜 알리미 - 윈도우 PC/노트북 설치 스크립트
#
# 이 폴더(hotdeal-alert)를 통째로 노트북에 복사한 뒤, 폴더 안에서 실행:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# 옵션
#   -LaptopPower   전원 연결 시 덮개를 닫아도 계속 켜두고, 절전 모드에 들어가지 않게 설정
#   -SkipTest      마지막 텔레그램 테스트 메시지를 보내지 않음
#   -Uninstall     작업 스케줄러 작업만 삭제 (폴더와 파일은 그대로)
#
# 관리자 권한은 필요 없습니다 (Python은 현재 사용자에게만 설치, 작업도 현재 사용자로 등록).
param([switch]$LaptopPower, [switch]$SkipTest, [switch]$Uninstall)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Dir      = $PSScriptRoot
$TaskName = 'HotdealAlert'
$PyDir    = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312'
$Py       = Join-Path $PyDir 'python.exe'
$Pyw      = Join-Path $PyDir 'pythonw.exe'

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }

if ($Uninstall) {
    Step '작업 스케줄러 작업 삭제'
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Ok "$TaskName 삭제됨"
    } else { Ok "$TaskName 작업이 없습니다" }
    return
}

# 1) 필요한 파일 확인
Step '파일 확인'
foreach ($f in 'hotdeal.py', 'config.json', 'requirements.txt', 'telegram_notify.py') {
    if (-not (Test-Path (Join-Path $Dir $f))) { throw "$f 가 없습니다. hotdeal-alert 폴더 안에서 실행하세요." }
}
Ok '프로그램 파일 있음'
$hasToken = Test-Path (Join-Path $Dir 'telegram_token.json')
if ($hasToken) { Ok 'telegram_token.json 있음' }
else { Warn 'telegram_token.json 이 없습니다. 원래 PC에서 복사하거나, 설치 후 telegram_setup.py 를 실행하세요.' }
if (Test-Path (Join-Path $Dir 'seen.json')) { Ok 'seen.json 있음 (이미 본 글은 다시 알리지 않음)' }
else { Warn 'seen.json 이 없습니다. 첫 실행은 기존 글을 기록만 하고 알림을 보내지 않습니다.' }

# 2) Python 3.12
Step 'Python 3.12'
if (Test-Path $Py) { Ok (& $Py --version) }
else {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'winget 이 없습니다. https://www.python.org/downloads/ 에서 Python 3.12 를 설치한 뒤 다시 실행하세요.'
    }
    winget install --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if (-not (Test-Path $Py)) { throw "Python 설치 후에도 $Py 를 찾지 못했습니다." }
    Ok (& $Py --version)
}

# 3) 패키지
Step '패키지 설치 (requests, beautifulsoup4)'
& $Py -m pip install --quiet --disable-pip-version-check --no-warn-script-location -r (Join-Path $Dir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip 설치 실패' }
Ok '설치 완료'

# 4) 사이트 접속 확인 (전송·기록 없음)
Step '사이트 접속 확인 (dry-run)'
$env:PYTHONIOENCODING = 'utf-8'
& $Py (Join-Path $Dir 'hotdeal.py') --dry-run
if ($LASTEXITCODE -ne 0) { Warn 'dry-run 이 실패했습니다. 위 오류를 확인하세요.' } else { Ok '확인 완료 (위 목록은 조건에 맞는 글이며, dry-run은 이미 알린 글도 보여줍니다)' }

# 5) 작업 스케줄러: 30분마다(매시 7분·37분) + 로그인할 때, 창 없이 실행
Step "작업 스케줄러 등록 ($TaskName)"
$action  = New-ScheduledTaskAction -Execute $Pyw -Argument "`"$Dir\hotdeal.py`"" -WorkingDirectory $Dir
$now     = Get-Date
$start   = $now.Date.AddHours($now.Hour).AddMinutes($(if ($now.Minute -lt 7) { 7 } elseif ($now.Minute -lt 37) { 37 } else { 67 }))
$every   = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 30)
$atLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$set     = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
           -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($every, $atLogon) -Settings $set `
    -Description 'Gift card hotdeal alert -> Telegram (every 30 min)' -Force | Out-Null
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Ok "등록됨. 다음 실행: $($info.NextRunTime)"

# 6) (선택) 노트북 전원 설정
if ($LaptopPower) {
    Step '노트북 전원 설정 (전원 연결 시)'
    powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0   # 덮개 닫음: 아무것도 안 함
    powercfg /change standby-timeout-ac 0                               # 절전 모드: 사용 안 함
    powercfg /change hibernate-timeout-ac 0                             # 최대 절전: 사용 안 함
    powercfg /setactive SCHEME_CURRENT
    Ok '덮개를 닫아도 켜져 있고, 전원 연결 시 절전하지 않습니다 (화면 끄기는 그대로).'
}

# 7) 텔레그램 테스트
if (-not $SkipTest -and $hasToken) {
    Step '텔레그램 테스트 메시지'
    & $Py (Join-Path $Dir 'hotdeal.py') --test
    if ($LASTEXITCODE -eq 0) { Ok '보냈습니다. 텔레그램 봇 대화방을 확인하세요.' } else { Warn '전송 실패. telegram_setup.py 로 다시 연결해 보세요.' }
}

Step '완료'
Write-Host @"
    - 실행 기록: $Dir\hotdeal.log
    - 원래 PC에서는 중복 알림을 막기 위해 작업을 꺼주세요:  Disable-ScheduledTask $TaskName
    - 노트북은 충전기에 연결하고, 제조사 프로그램에서 배터리 충전 한도(예: 80%)를 켜두면 좋습니다.
    - 윈도우 업데이트로 재부팅되면 로그인할 때까지 멈춥니다. 노트북 전용이면 자동 로그인을 고려하세요.
"@
