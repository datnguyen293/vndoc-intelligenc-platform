<#
    install-service.ps1 — đăng ký VNDoc OCR Service bằng NSSM (DOC-11 §3).

    Inno Setup gọi script này ở [Run] (hoặc admin chạy tay để cài dịch vụ trên bản staging).
    Yêu cầu: chạy với quyền Administrator.

    Tham số:
      -InstallRoot  thư mục cài (chứa runtime\, launcher.py, nssm.exe, config\, logs\)

    Idempotent: nếu service đã tồn tại thì gỡ trước rồi cài lại.
#>
param(
    [Parameter(Mandatory = $true)] [string] $InstallRoot
)

$ErrorActionPreference = 'Stop'

$ServiceName = 'VNDocOCR'
$DisplayName = 'VNDoc OCR Service'
$Nssm        = Join-Path $InstallRoot 'nssm.exe'
$PythonExe   = Join-Path $InstallRoot 'runtime\python.exe'
$Launcher    = Join-Path $InstallRoot 'launcher.py'
$LogDir      = Join-Path $InstallRoot 'logs'

foreach ($p in @($Nssm, $PythonExe, $Launcher)) {
    if (-not (Test-Path $p)) { throw "Thiếu tệp bắt buộc: $p" }
}
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# Gỡ service cũ nếu có (cài lại sạch).
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service '$ServiceName' đã tồn tại → gỡ để cài lại..."
    & $Nssm stop $ServiceName confirm 2>$null
    & $Nssm remove $ServiceName confirm
    Start-Sleep -Seconds 1
}

Write-Host "Đăng ký service '$ServiceName'..."
& $Nssm install $ServiceName $PythonExe $Launcher
& $Nssm set $ServiceName DisplayName $DisplayName
& $Nssm set $ServiceName Description 'OCR giấy tờ tuỳ thân VN — FastAPI offline (127.0.0.1:11001)'
& $Nssm set $ServiceName AppDirectory $InstallRoot
& $Nssm set $ServiceName Start SERVICE_AUTO_START

# Tự restart khi crash (NFR-002): NSSM khởi động lại tiến trình, có throttle chống loop.
& $Nssm set $ServiceName AppExit Default Restart
& $Nssm set $ServiceName AppRestartDelay 3000
& $Nssm set $ServiceName AppThrottle 5000

# Log stdout/err + xoay vòng theo dung lượng (10 MB), giữ khi restart (append).
& $Nssm set $ServiceName AppStdout (Join-Path $LogDir 'service.out.log')
& $Nssm set $ServiceName AppStderr (Join-Path $LogDir 'service.err.log')
& $Nssm set $ServiceName AppStdoutCreationDisposition 4
& $Nssm set $ServiceName AppStderrCreationDisposition 4
& $Nssm set $ServiceName AppRotateFiles 1
& $Nssm set $ServiceName AppRotateOnline 1
& $Nssm set $ServiceName AppRotateBytes 10485760

Write-Host "Khởi động service..."
& $Nssm start $ServiceName

# Kiểm tra health (chờ tối đa ~30s vì lần đầu nạp model chậm).
$healthUrl = 'http://127.0.0.1:11001/api/v1/health'
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 -ErrorAction Stop
        if ($r.status -eq 'ok') { $ok = $true; break }
    } catch { }
}
if ($ok) {
    Write-Host "✅ VNDoc OCR Service đã chạy: $healthUrl"
} else {
    Write-Warning "Service đã cài nhưng /health chưa phản hồi. Xem log tại: $LogDir"
    exit 1
}
