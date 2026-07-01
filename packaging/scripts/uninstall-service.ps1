<#
    uninstall-service.ps1 — gỡ VNDoc OCR Service (DOC-11 §6).
    Inno Setup gọi ở [UninstallRun]. Giữ nguyên config\ và logs\ (không xoá dữ liệu admin).
#>
param(
    [Parameter(Mandatory = $true)] [string] $InstallRoot
)

$ErrorActionPreference = 'SilentlyContinue'

$ServiceName = 'VNDocOCR'
$Nssm = Join-Path $InstallRoot 'nssm.exe'

if (Test-Path $Nssm) {
    & $Nssm stop $ServiceName confirm
    & $Nssm remove $ServiceName confirm
    Write-Host "Đã gỡ service '$ServiceName'."
} else {
    # Dự phòng nếu thiếu nssm.exe.
    sc.exe stop $ServiceName | Out-Null
    sc.exe delete $ServiceName | Out-Null
}
