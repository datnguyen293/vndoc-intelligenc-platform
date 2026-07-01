<#
    init-config.ps1 — chuẩn bị config lần cài đầu (DOC-11 §7, DEC-088).

    - Tạo  config\vndoc.env  từ  vndoc.env.example  nếu CHƯA có.
    - Nếu  DIP_API_KEY  còn TRỐNG → SINH KEY NGẪU NHIÊN (64 hex) và ghi vào.
    - Idempotent: đã có key (admin đặt hoặc lần cài trước) → GIỮ NGUYÊN, không đè.

    Inno Setup gọi ở [Run] TRƯỚC install-service để service khởi động đã có key.
#>
param(
    [Parameter(Mandatory = $true)] [string] $InstallRoot
)

$ErrorActionPreference = 'Stop'

$cfgDir  = Join-Path $InstallRoot 'config'
$cfg     = Join-Path $cfgDir 'vndoc.env'
$example = Join-Path $cfgDir 'vndoc.env.example'

if (-not (Test-Path $cfgDir)) { New-Item -ItemType Directory -Path $cfgDir | Out-Null }
if (-not (Test-Path $cfg)) {
    if (Test-Path $example) { Copy-Item $example $cfg } else { New-Item -ItemType File -Path $cfg | Out-Null }
}

$content = Get-Content $cfg -Raw -ErrorAction SilentlyContinue
if ($null -eq $content) { $content = '' }

# Đã có key thật (DIP_API_KEY=<không rỗng> TRÊN CÙNG DÒNG) → không làm gì.
# Dùng [^\S\r\n] (khoảng trắng ngang, KHÔNG gồm newline) để không "ăn" sang dòng comment kế.
if ([regex]::IsMatch($content, '(?m)^[^\S\r\n]*DIP_API_KEY[^\S\r\n]*=[^\S\r\n]*\S')) {
    Write-Host "DIP_API_KEY đã có — giữ nguyên."
    return
}

# Sinh 32 byte ngẫu nhiên bảo mật → 64 ký tự hex.
$bytes = New-Object 'System.Byte[]' 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$key = -join ($bytes | ForEach-Object { $_.ToString('x2') })

if ([regex]::IsMatch($content, '(?m)^\s*DIP_API_KEY\s*=')) {
    $content = [regex]::Replace($content, '(?m)^\s*DIP_API_KEY\s*=.*$', "DIP_API_KEY=$key")
} else {
    $content = $content.TrimEnd() + "`r`nDIP_API_KEY=$key`r`n"
}

# Ghi UTF-8 KHÔNG BOM (python-dotenv đọc dòng đầu có BOM sẽ lỗi khoá).
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($cfg, $content, $utf8NoBom)

Write-Host "Đã sinh API Key ngẫu nhiên cho lần cài đầu (client Android dùng key này)."
Write-Host "API Key: $key"
