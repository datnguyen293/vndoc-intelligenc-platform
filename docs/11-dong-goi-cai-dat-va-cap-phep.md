# DOC-11 — Đóng gói, Cài đặt & Cấp phép (Packaging / Delivery)

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-03 (kiến trúc), DOC-04 (ADR), DOC-10 (triển khai/hiệu năng)
- **Truy vết:** NFR-002 (tự khởi động/restart), NFR-007 (bảo mật), NFR-008 (RAM),
  FR-016, FR-018 (tách config/model ngoài mã), + yêu cầu sản phẩm hoá của anh Đạt.

> Mục tiêu giai đoạn này: biến service đang chạy bằng `uvicorn` (dev) thành **một sản
> phẩm giao ra thị trường**: cán bộ **double-click bộ cài** → máy có sẵn Windows Service
> nghe `:11001`, **không lộ mã nguồn Python**, admin nhập được API Key qua file config,
> và (bước sau) **kích hoạt license theo từng máy**.

---

## 1. Bốn yêu cầu & cách đáp ứng

| # | Yêu cầu | Giải pháp chốt | Mục |
|---|---|---|---|
| 1 | Bộ cài double-click là chạy | **Inno Setup → 1 file `VNDoc-Setup-x.y.z.exe`** | §4, §6 |
| 2 | Chạy như Windows Service, FastAPI `:11001` | **NSSM** bọc `launcher` chạy uvicorn `:11001` | §3, §5 |
| 3 | Admin nhập API Key qua config | **File `config\vndoc.env`** (`DIP_*`) + restart service; **tự sinh key lần đầu** | §7 |
| 4 | Mã hoá source, không giao clear-source | **PyArmor** obfuscate code của mình; thư viện giữ nguyên wheel | §8 |
| 5 | Android LAN truy cập được + an toàn | Bind `0.0.0.0` + **whitelist IP** (mặc định `127.0.0.1`, `192.168.0.0/24`) | §7.2 |
| (sau) | License kích hoạt theo máy | **Machine fingerprint + license file** (nền PyArmor / tự ký) | §9 |

**Quyết định nền (do anh Đạt chốt 2026-07-01):**
- **DEC-080**: Bảo vệ source bằng **PyArmor** (obfuscate + bytecode encrypt; là nền cho
  license khoá-máy ở §9). KHÔNG dùng Nuitka/Cython/pyc-only.
- **DEC-081**: Bộ cài **EXE (Inno Setup)** — cài **thủ công từng máy**, KHÔNG cần MSI/GPO
  (không có triển khai tập trung/từ xa).
- **DEC-082**: Cấu hình bằng **file config** (`.env` khoá `DIP_*`), sửa xong **restart
  service**; CHƯA làm GUI settings ở V1.
- **DEC-083**: Cổng mặc định **11001**. Bind **`0.0.0.0`** (Android LAN gọi được) + **whitelist
  IP** giữ an toàn (DEC-087) — xem §7.2/NFR-007.
- **DEC-087**: Kiểm soát truy cập bằng **whitelist CIDR** (`DIP_ALLOWED_IPS`, mặc định
  `127.0.0.1/32,192.168.0.0/24`) qua middleware; client ngoài dải → `403`.
- **DEC-088**: **Tự sinh API Key** ngẫu nhiên (64-hex) lần cài đầu nếu để trống; idempotent.

---

## 2. Sản phẩm bàn giao (deliverables) & bố cục cài đặt

Bộ cài đặt trải ra thư mục (mặc định `C:\Program Files\VNDoc\` — đặt được lúc cài):

```text
C:\Program Files\VNDoc\
├── runtime\               # Python nhúng 3.11 (python-build-standalone) + DEPS CPU cài sẵn
│   ├── python.exe         #   (fastapi, uvicorn, torch-CPU, opencv, vietocr, rapidocr, zxing...)
│   └── Lib\site-packages\ #   thư viện nằm TRONG runtime (không tách riêng) → import chuẩn
├── pyarmor_runtime_000000\ # runtime giải mã PyArmor (sinh kèm khi obfuscate)
├── app\                   # ⚠️ CODE CỦA TA — đã PyArmor obfuscate (.py bị thay bằng bản mã hoá)
├── rectifier\             # ⚠️ CODE CỦA TA — đã obfuscate
├── plugins\               # manifest YAML (KHÔNG mã hoá — dữ liệu khai báo, cho phép cập nhật)
├── models\                # weights offline: vgg_seq2seq.pth, rapidocr *.onnx (bundle sẵn)
├── config\
│   └── vndoc.env          # ⚙️ admin sửa (API key, port, device...) — xem §7
├── logs\                  # log xoay vòng, đã mask số định danh (NFR-007)
├── launcher.py            # entrypoint production đã PyArmor mã hoá (chạy uvicorn :11001) — §5
├── nssm.exe               # đăng ký/gỡ Windows Service — §3
├── license\               # (bước sau §9) license.key + machine fingerprint
└── VERSION                # phiên bản service + plugin
```

**Nguyên tắc tách lớp (FR-018):** `models/ plugins/ config/ logs/` nằm NGOÀI code, cập
nhật được mà không đụng bản obfuscate. `app/ rectifier/` là tài sản trí tuệ → mã hoá.
`plugins/*.yaml` cố ý để rõ (khai báo, không phải bí mật) — thêm loại giấy tờ = thả manifest.

---

## 3. Windows Service (NSSM) — DEC-071/NFR-002

- Bọc `launcher` bằng **NSSM** (public-domain, 1 exe, bundle kèm):
  - `Start=SERVICE_AUTO_START` — tự chạy cùng Windows.
  - `AppExit Default Restart` + throttle — **tự restart khi crash** (NFR-002).
  - Chuyển hướng stdout/stderr → `logs\service.out.log` / `service.err.log` (NSSM tự xoay theo dung lượng).
  - Tên service: `VNDocOCR`; DisplayName: "VNDoc OCR Service".
- Vòng đời do installer gọi (§6): `nssm install` khi cài, `nssm remove` khi gỡ.
- Vận hành thủ công: `sc start VNDocOCR` / `sc stop VNDocOCR`, hoặc services.msc.

> Vì sao NSSM chứ không phải pywin32 service: NSSM tách biệt hẳn logic khỏi mã Python
> (không phải nhét mã service vào app — hợp với việc app đã bị obfuscate), tự lo restart/log
> xoay vòng, và đã là quyết định DOC-10 (DEC-071).

## 4. Vì sao embeddable Python + PyArmor (không PyInstaller onefile)

- Deps nặng & động (`torch`, `opencv`, `vietocr`, `onnxruntime`, `zxing-cpp`) khiến
  **PyInstaller onefile** hay lỗi hidden-import, khởi động chậm (giải nén tạm), khó vá.
- Hướng bền: **python-build-standalone** (bản Python nhúng độc lập) + `site-packages`
  cài sẵn từ `requirements.txt`. Chỉ **code của ta** đi qua **PyArmor** → thư viện vẫn là
  wheel bình thường (không cần obfuscate, không phải bí mật). Khởi động nhanh, dễ vá lẻ.
- Đổi lại bộ cài to (~1.5–2.5 GB do torch+models). Chấp nhận: cài **offline**, 1 lần/máy.
  Muốn nhẹ hơn: bản **CPU torch** (không CUDA) — xem §10.

## 5. `launcher` — entrypoint production

Thay cho `uvicorn app.main:app` (dev). Nhiệm vụ:
1. Nạp cấu hình từ `config\vndoc.env` (đặt `VNDOC_CONFIG` trỏ tới file này — settings đọc, §7).
2. Trỏ `DIP_MODELS_DIR`, `DIP_PLUGINS_DIR` vào thư mục cài đặt (không phụ thuộc CWD).
3. Chạy `uvicorn.run(app, host=settings.host, port=settings.port)` — mặc định `127.0.0.1:11001`.
4. (Bước sau §9) kiểm tra license trước khi `serve`; thiếu/không hợp lệ → thoát mã lỗi rõ ràng.

`launcher` là file được PyArmor bảo vệ; NSSM gọi `runtime\python.exe launcher.py`.

## 6. Inno Setup — kịch bản cài đặt (DEC-081)

`packaging/installer/vndoc.iss` sinh `VNDoc-Setup-x.y.z.exe`. Luồng cài:
1. Yêu cầu quyền admin (đăng ký service cần).
2. Chép `runtime/ site-packages/ app/ rectifier/ plugins/ models/ nssm.exe launcher`.
3. Chép `config\vndoc.env` **chỉ khi chưa tồn tại** (không đè config admin đã sửa khi nâng cấp).
4. `[Run]`: `nssm install VNDocOCR ...` → `nssm set ...` (AUTO_START, restart, log) → `sc start`.
5. Kiểm tra `http://127.0.0.1:11001/api/v1/health` → báo cài đặt thành công.
6. `[UninstallRun]`: `sc stop` → `nssm remove VNDocOCR confirm`. Giữ lại `config/ logs/` (tuỳ chọn).

Nâng cấp: cài đè cùng thư mục; giữ `config/` & `models/`; restart service.

## 7. Cấu hình, API Key & Whitelist IP (DEC-082/083/087/088, NFR-007)

- File `config\vndoc.env` (khoá theo `env_prefix=DIP_` sẵn có của `settings.py`). Ví dụ:

  ```ini
  DIP_API_KEY=<tự sinh khi cài>        # client Android gửi header X-API-Key
  DIP_ALLOWED_IPS=127.0.0.1/32,192.168.0.0/24   # whitelist CIDR — client ngoài dải → 403
  DIP_HOST=0.0.0.0                     # nghe mọi giao diện để Android LAN gọi được
  DIP_PORT=11001
  DIP_OCR_DEVICE=auto                  # auto|cpu|cuda
  DIP_MAX_CONCURRENCY=8                # ~ số P-core i7-14700
  DIP_REQUEST_TIMEOUT_SEC=15
  ```

### 7.1 API Key — TỰ SINH lần cài đầu (DEC-088)
- **API Key** = **secret dùng chung** client Android gửi qua `X-API-Key`. Cơ chế **đã có**
  (`settings.api_key` + `_check_api_key` trong `routes.py`): đặt key → mọi request thiếu/sai
  key bị `401`. (Service offline, KHÔNG có "API key gọi OCR đám mây".)
- **`init-config.ps1`** (bộ cài gọi ở `[Run]` TRƯỚC khi service chạy): nếu `DIP_API_KEY`
  còn trống thì **sinh 64-hex ngẫu nhiên** (`RandomNumberGenerator`) ghi vào `vndoc.env`,
  in ra màn hình để bàn giao cho app Android. **Idempotent**: đã có key → giữ nguyên (nâng
  cấp không đổi key). Ghi UTF-8 **không BOM** (python-dotenv đọc dòng đầu có BOM sẽ lỗi).

### 7.2 Whitelist IP — cho Android cùng LAN (DEC-087)
- Thiết bị Android **cùng LAN** với máy, **không** gọi được qua `127.0.0.1` → service phải
  **bind `0.0.0.0`**. An toàn nhờ **whitelist dải CIDR** ở tầng ứng dụng: `IPWhitelistMiddleware`
  (`app/security.py`) chặn client IP ngoài `DIP_ALLOWED_IPS` bằng `403`.
- Mặc định `127.0.0.1/32,192.168.0.0/24`; admin sửa cho khớp subnet đơn vị (vd `10.0.0.0/24`).
  Rỗng = tắt whitelist. Host không phải IP (Starlette `TestClient`) → bỏ qua (test chạy được).
- **Tường lửa**: `install-service.ps1` tự `netsh` mở cổng `11001` (TCP inbound, profile
  private+domain) khi cài; `uninstall-service.ps1` xoá luật khi gỡ (phòng thủ nhiều lớp).

### 7.4 Hướng dẫn cho cán bộ triển khai
`packaging/HUONG-DAN-CAI-DAT.md` — tài liệu **cho người cài** (không kỹ thuật): cài EXE, lấy
API Key, chỉnh dải IP LAN, bật/tắt service, cấu hình Android, xử lý sự cố. Bộ cài ship file này
vào `{app}` + tạo shortcut Start Menu + hỏi mở sau khi cài.

### 7.3 Nạp config & vận hành
- `settings.py` sửa (bổ sung, an toàn) để đọc file trỏ bởi env `VNDOC_CONFIG`; không đặt thì
  giữ hành vi cũ (`service/.env`). **Đã test: golden 81 passed** (gồm test whitelist 403/LAN).
- Đổi config → **restart service** (`sc stop/start VNDocOCR`). CHƯA hot-reload ở V1.
- Bảo mật: hạn chế NTFS ACL cho `config\` (chứa key) & `logs\`; log **mask** số định danh (DOC-10 §6).

## 8. Bảo vệ source bằng PyArmor (DEC-080)

- Phạm vi obfuscate: `service/app/**`, `rectifier/**`, `launcher` — **toàn bộ IP của ta**.
  KHÔNG obfuscate: `site-packages` (thư viện bên thứ ba), `plugins/*.yaml` (khai báo).
- Kỹ thuật: PyArmor `gen` (bytecode encryption + runtime key). Bản `.py` gốc **không**
  đi kèm bộ cài; chỉ ship bản đã mã hoá + runtime PyArmor.
- Kiểm thử sau obfuscate: chạy **health + 1 ảnh mẫu mỗi loại** trên bản đã đóng gói để chắc
  PyArmor không phá dynamic import (torch/opencv hay import động). Ghi lại ở runbook.
- Ràng buộc: PyArmor bản trả phí mở khoá **license khoá phần cứng** (§9) & hết hạn — mua
  khi lên kế hoạch phát hành. Bản free đủ để obfuscate cơ bản (làm trước, license thêm sau).

## 9. Cấp phép theo máy — LÊN KẾ HOẠCH (chưa làm V1)

> Ghi lại theo note của anh: "nghĩ cơ chế cấp license để activate theo mỗi máy tính."

- **Machine fingerprint**: kết hợp định danh ổn định của máy — vd Volume Serial ổ hệ thống,
  UUID máy (`wmic csproduct get uuid`), MAC card mạng chính — băm SHA-256 thành `machineId`.
- **Luồng kích hoạt (offline-friendly)**:
  1. Bộ cài/CLI in ra `machineId` của máy khách.
  2. Nhà cung cấp ký `license.key` (chứa `machineId`, hạn dùng, loại giấy tờ được phép…)
     bằng **khoá riêng** (Ed25519/RSA); public key nhúng trong app.
  3. `launcher` xác minh chữ ký + `machineId` khớp trước khi `serve`; sai → từ chối chạy.
- **Hai lựa chọn triển khai** (chốt ở DOC-11 v0.2):
  - **PyArmor Pro outer license**: khoá bản obfuscate theo phần cứng + hạn dùng — ít code,
    dùng luôn hạ tầng §8.
  - **License tự ký**: linh hoạt hơn (nhúng quyền theo loại giấy tờ), nhưng tự viết verify.
- Chống chỉnh giờ (đổi ngày để lách hạn), gia hạn, thu hồi: bàn ở v0.2.
- **V1 không chặn theo license** để không cản kiểm thử; chỉ chuẩn bị điểm móc trong `launcher`.

## 10. Kích thước & biến thể build

- **CPU-only (mặc định giao hàng)**: torch CPU → bộ cài gọn hơn, chạy mọi máy (ADR-002).
  `DIP_OCR_DEVICE=auto` vẫn tự lùi CPU. Máy đích i7-14700 đủ nhanh (DOC-10 §8b).
- **GPU (tuỳ chọn)**: bản kèm torch CUDA cho máy có NVIDIA — bộ cài lớn (~+2.5 GB). Chỉ dựng
  khi khách yêu cầu; không mặc định.
- Models bundle offline (không tải lúc chạy — máy đích không Internet): `vgg_seq2seq.pth`,
  RapidOCR `*.onnx`. Đặt trong `models\`, trỏ bằng `DIP_MODELS_DIR`.

## 11. Runbook build (tóm tắt — chi tiết ở `packaging/README.md`)

Chuẩn bị 1 lần (đã tự động khi setup): `packaging\runtime\` (Python 3.11 + deps CPU + pyarmor),
`packaging\bin\nssm.exe`, `service\models\vgg_seq2seq.pth`.

```powershell
# 1. Build staging (obfuscate + copy runtime/models/plugins/config/scripts) — MỘT LỆNH:
powershell -ExecutionPolicy Bypass -File packaging\scripts\build.ps1
# 2. (khuyến nghị) chạy thử bundle trước khi nén:
build\stage\init-config.ps1 -InstallRoot build\stage        # sinh key
build\stage\runtime\python.exe build\stage\launcher.py       # GET :11001/api/v1/health
# 3. Nén bộ cài (cần Inno Setup):
iscc packaging\installer\vndoc.iss    # → packaging\installer\Output\VNDoc-Setup-x.y.z.exe
```

> Đã kiểm chứng: bundle obfuscate chạy thật OK — `/health modelsWarm:true`, `/extract` đọc QR
> BHYT (`idNumber`, `fullName`), thiếu `X-API-Key` → 401. Chỉ còn cài Inno Setup + chạy `iscc`.

## 12. Quyết định khoá (mới)

| ID | Quyết định |
|---|---|
| DEC-080 | Bảo vệ source = **PyArmor** (nền cho license khoá-máy) |
| DEC-081 | Bộ cài **Inno Setup EXE**, cài thủ công từng máy (không MSI/GPO) |
| DEC-082 | Cấu hình bằng **file `config\vndoc.env`** (`DIP_*`), sửa xong restart; chưa GUI |
| DEC-083 | Cổng **11001**, chỉ nghe `127.0.0.1` (nội bộ máy) |
| DEC-084 | Đóng gói **embeddable Python + site-packages + PyArmor**, KHÔNG PyInstaller onefile |
| DEC-085 | Service **NSSM** (auto-start, auto-restart, log xoay) — kế thừa DEC-071 |
| DEC-086 | License khoá-máy: **chuẩn bị điểm móc ở `launcher`**, bật ở phiên bản sau (v0.2) |
| DEC-087 | **Whitelist IP** (CIDR) chặn truy cập FastAPI; bind 0.0.0.0 cho Android LAN |
| DEC-088 | **Tự sinh API Key** ngẫu nhiên lần cài đầu (`init-config.ps1`), idempotent |

## 13. Việc tiếp theo (triển khai theo thứ tự)

1. **Khung `packaging/`** + sửa `settings.py` đọc `VNDOC_CONFIG` (an toàn, golden test xanh). ← làm trước
2. `launcher` + `config\vndoc.env.example` + script NSSM (`install-service.ps1`).
3. Script build: staging site-packages CPU + PyArmor + copy models/plugins.
4. `vndoc.iss` (Inno Setup) → bộ cài thử trên máy sạch.
5. (v0.2) machine fingerprint + verify license trong `launcher` (§9).
```

