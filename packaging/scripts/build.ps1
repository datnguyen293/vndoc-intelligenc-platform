<#
    build.ps1 — dựng thư mục staging đã đóng gói để Inno Setup nén lại (DOC-11 §11).

    Các bước (đã tự động hoá gần hết):
      1. Làm sạch staging.
      2. PyArmor obfuscate  service\app + rectifier + launcher  → staging\ (DOC-11 §8),
         DÙNG CHÍNH Python nhúng 3.11 để runtime PyArmor khớp phiên bản bundle.
      3. Chép plugins\ (YAML, KHÔNG mã hoá), config mẫu, nssm.exe, script service.
      4. Chép runtime Python (đã cài sẵn deps CPU) + models\ (weights offline).

    KHÔNG obfuscate deps trong runtime (thư viện bên thứ ba) và plugins\*.yaml (khai báo).

    Chuẩn bị 1 lần (đã làm nếu theo hướng dẫn):
      - packaging\runtime\  = Python nhúng 3.11 + deps (packaging\requirements-runtime.txt) + pyarmor
      - packaging\bin\nssm.exe
      - service\models\vgg_seq2seq.pth  (weight VietOCR offline)

    Chạy:  powershell -ExecutionPolicy Bypass -File packaging\scripts\build.ps1
    Sau đó: iscc packaging\installer\vndoc.iss
#>
param(
    [string] $StageDir = (Join-Path $PSScriptRoot '..\..\build\stage'),
    [string] $RuntimeSrc = (Join-Path $PSScriptRoot '..\runtime'),   # Python nhúng + deps
    [string] $ModelsSrc  = (Join-Path $PSScriptRoot '..\..\service\models'),
    [switch] $SkipObfuscate   # dựng bản staging KHÔNG mã hoá để test nhanh (dev)
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$Pkg      = Join-Path $RepoRoot 'packaging'
$PyExe    = Join-Path $RuntimeSrc 'python.exe'

Write-Host "RepoRoot   = $RepoRoot"
Write-Host "StageDir   = $StageDir"
Write-Host "RuntimeSrc = $RuntimeSrc"

# 1) Làm sạch staging -------------------------------------------------------
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Path $StageDir | Out-Null
New-Item -ItemType Directory -Path (Join-Path $StageDir 'logs') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $StageDir 'config') | Out-Null

# 2) PyArmor obfuscate code của ta -----------------------------------------
$srcApp   = Join-Path $RepoRoot 'service\app'
$srcRect  = Join-Path $RepoRoot 'rectifier\rectifier'   # package con (rectifier\rectifier\)
$launcher = Join-Path $Pkg 'launcher.py'

if ($SkipObfuscate) {
    Write-Warning "SkipObfuscate: chép source THÔ (chỉ để test staging, KHÔNG giao hàng)."
    Copy-Item $srcApp  (Join-Path $StageDir 'app')       -Recurse
    Copy-Item (Join-Path $RepoRoot 'rectifier\rectifier') (Join-Path $StageDir 'rectifier') -Recurse
    Copy-Item $launcher (Join-Path $StageDir 'launcher.py')
} else {
    if (-not (Test-Path $PyExe)) { throw "Thiếu runtime nhúng: $PyExe (xem README §chuẩn bị)" }
    # Obfuscate BẰNG Python nhúng 3.11 → pyarmor_runtime khớp bundle. -r đệ quy package.
    Write-Host "PyArmor obfuscate (bằng runtime 3.11) app + rectifier + launcher..."
    & $PyExe -m pyarmor.cli gen -O $StageDir -r $srcApp $srcRect $launcher
    if ($LASTEXITCODE -ne 0) { throw "PyArmor gen lỗi (exit $LASTEXITCODE)" }
    # Kết quả: staging\app, staging\rectifier, staging\launcher.py (mã hoá) + pyarmor_runtime_000000\.
}

# 3) Tài nguyên KHÔNG mã hoá ------------------------------------------------
Copy-Item (Join-Path $RepoRoot 'service\plugins') (Join-Path $StageDir 'plugins') -Recurse
Copy-Item (Join-Path $Pkg 'config\vndoc.env.example') (Join-Path $StageDir 'config\vndoc.env.example')
Copy-Item (Join-Path $Pkg 'scripts\init-config.ps1')       $StageDir
Copy-Item (Join-Path $Pkg 'scripts\install-service.ps1')   $StageDir
Copy-Item (Join-Path $Pkg 'scripts\uninstall-service.ps1') $StageDir

$nssm = Join-Path $Pkg 'bin\nssm.exe'
if (Test-Path $nssm) { Copy-Item $nssm $StageDir } else {
    Write-Warning "Thiếu packaging\bin\nssm.exe — tải từ nssm.cc rồi đặt vào đó (xem README)."
}

# 4) Runtime Python (kèm deps CPU) + models offline ------------------------
Write-Host "Chép runtime nhúng (kèm deps) → staging\runtime ... (nặng, chờ chút)"
Copy-Item $RuntimeSrc (Join-Path $StageDir 'runtime') -Recurse

if (Test-Path (Join-Path $ModelsSrc 'vgg_seq2seq.pth')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $StageDir 'models') | Out-Null
    Copy-Item (Join-Path $ModelsSrc '*') (Join-Path $StageDir 'models') -Recurse
    Write-Host "Chép models\ offline OK."
} else {
    Write-Warning "Thiếu $ModelsSrc\vgg_seq2seq.pth — VietOCR sẽ phải tải mạng (không hợp máy offline)."
}

Write-Host ""
Write-Host "== Staging XONG: $StageDir =="
Write-Host "Chạy thử:  $StageDir\runtime\python.exe $StageDir\launcher.py  → GET http://127.0.0.1:11001/api/v1/health"
Write-Host "Nén bộ cài: iscc packaging\installer\vndoc.iss"
