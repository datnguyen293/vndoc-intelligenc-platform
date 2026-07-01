# packaging/ — Đóng gói VNDoc OCR Service thành bộ cài Windows

Hiện thực **DOC-11** (Đóng gói, Cài đặt & Cấp phép). Kết quả cuối:
`VNDoc-Setup-x.y.z.exe` — cán bộ double-click → máy có **Windows Service `VNDocOCR`**
chạy FastAPI ở **`127.0.0.1:11001`**, **không lộ source** (PyArmor), admin nhập API Key
qua `config\vndoc.env`.

## Thành phần

| Đường dẫn | Vai trò |
|---|---|
| `launcher.py` | Entrypoint production: chạy uvicorn `:11001`, tự trỏ config/models/plugins (DOC-11 §5) |
| `config/vndoc.env.example` | Mẫu cấu hình (API key, whitelist IP, port, device) — bộ cài chép thành `config\vndoc.env` |
| `scripts/build.ps1` | Dựng staging: PyArmor obfuscate `app`+`rectifier`+`launcher`, chép plugins/config/nssm |
| `scripts/init-config.ps1` | Lần cài đầu: tạo `vndoc.env` + **sinh API Key ngẫu nhiên** (idempotent) |
| `scripts/install-service.ps1` | Đăng ký service qua NSSM (Inno gọi ở `[Run]`; auto-start + auto-restart + log) |
| `scripts/uninstall-service.ps1` | Gỡ service (Inno gọi ở `[UninstallRun]`) |
| `installer/vndoc.iss` | Inno Setup → `VNDoc-Setup-x.y.z.exe` (ship kèm hướng dẫn + shortcut) |
| `HUONG-DAN-CAI-DAT.md` | **Hướng dẫn cho cán bộ triển khai** (ship vào `{app}` + Start Menu) |
| `bin/nssm.exe` | *(tự tải)* NSSM public-domain — KHÔNG commit (xem `.gitignore`) |

## Chuẩn bị (một lần) — phần lớn ĐÃ tự động

Đã dựng sẵn (script tải/cài hộ): `packaging\runtime\` (Python 3.11 nhúng + deps CPU +
pyarmor), `packaging\bin\nssm.exe`, `service\models\vgg_seq2seq.pth`. Chỉ còn **1 việc thủ
công**:

- **Inno Setup 6** để có `iscc.exe`: tải https://jrsoftware.org/isdl.php → cài. `iscc.exe`
  nằm ở `C:\Program Files (x86)\Inno Setup 6\` — thêm vào PATH hoặc gọi bằng đường dẫn đầy đủ.

Dựng lại runtime nếu cần từ đầu (đã có sẵn nên KHÔNG cần chạy lại):
```powershell
packaging\runtime\python.exe -m pip install -r packaging\requirements-runtime.txt
packaging\runtime\python.exe -m pip install pyarmor
```

## Quy trình build (DOC-11 §11)

```powershell
# 1) Build staging — obfuscate (bằng runtime 3.11) + copy runtime/models/plugins/config/scripts:
powershell -ExecutionPolicy Bypass -File packaging\scripts\build.ps1
#    Dev thử nhanh KHÔNG mã hoá: thêm -SkipObfuscate

# 2) (khuyến nghị) chạy thử bundle trước khi nén:
build\stage\init-config.ps1 -InstallRoot build\stage       # sinh API key
build\stage\runtime\python.exe build\stage\launcher.py      # rồi GET :11001/api/v1/health

# 3) Nén bộ cài (cần Inno Setup):
iscc packaging\installer\vndoc.iss
#    → packaging\installer\Output\VNDoc-Setup-0.1.0.exe   ← file giao khách
```

> ✅ Đã kiểm chứng bundle obfuscate chạy thật: `/health modelsWarm:true`, `/extract` đọc QR
> BHYT ra `idNumber`+`fullName`, thiếu `X-API-Key` → 401.

## Sau khi cài (máy khách)

Bộ cài **tự sinh API Key** lần đầu (in ra khi cài). Xem lại/đổi + chỉnh whitelist LAN:

```powershell
notepad "C:\Program Files\VNDoc\config\vndoc.env"
#   DIP_API_KEY=...            (đã tự sinh — bàn giao chuỗi này cho app Android)
#   DIP_ALLOWED_IPS=127.0.0.1/32,192.168.0.0/24   (sửa cho khớp subnet LAN đơn vị)
#   DIP_HOST=0.0.0.0          (để Android cùng LAN gọi được)
sc stop VNDocOCR ; sc start VNDocOCR

# Kiểm tra tại máy:
curl http://127.0.0.1:11001/api/v1/health
# Từ Android/LAN: http://<IP-máy>:11001/api/v1/health  (IP phải thuộc DIP_ALLOWED_IPS)
```

## Lưu ý

- **Chỉ code của ta bị obfuscate** (`app/`, `rectifier/`, `launcher`). Thư viện (trong
  `runtime\Lib\site-packages`) và `plugins/*.yaml` (khai báo, cho phép cập nhật) để nguyên.
- **CPU-only là bản giao mặc định** (ADR-002); bản GPU (torch CUDA) chỉ dựng khi khách cần
  (bộ cài +~2.5 GB) — xem DOC-11 §10.
- **License khoá-máy** (DOC-11 §9) chưa bật ở V1: `launcher` đã chừa điểm móc `verify_or_exit`.
- Không commit binary nặng: `build/`, `packaging/bin/nssm.exe`, runtime, models → `.gitignore`.
