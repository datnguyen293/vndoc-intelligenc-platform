# DOC-09 — Android Capture SDK

- **Trạng thái:** DESIGN (chốt để code)
- **Phiên bản:** 0.2
- **Phụ thuộc:** DOC-07 (API), DOC-11 (đóng gói/whitelist)
- **Truy vết:** FR-001, FR-002 (client), NFR-007, DEC-047 (hint bắt buộc), DEC-087 (whitelist)

## 1. Vai trò & phạm vi

Android **chỉ**: chụp ảnh tốt → gửi OCR service (LAN) → hiển thị kết quả cho cán bộ **sửa
tay** → trả về app nghiệp vụ. **KHÔNG** OCR trên thiết bị (DEC-002).

## 2. Quyết định chốt (brainstorm 2026-07-01)

| ID | Quyết định |
|---|---|
| DEC-064 | Đóng gói **thư viện AAR** `vndoc-sdk` (tái sử dụng) **+ app mẫu** demo/test |
| DEC-065 | **Kotlin**, minSdk **30 (Android 11+)**, CameraX + **Jetpack Compose** + Coroutines |
| DEC-066 | Cấu hình server **nhập tay** (Settings): host/port/API key → **EncryptedSharedPreferences** |
| DEC-067 | Truyền **HTTP** trên LAN cô lập (dựa whitelist IP + API key; chưa TLS) |
| DEC-068 | `docTypeHint` **BẮT BUỘC** — cán bộ chọn loại/họ trước khi chụp (khớp DEC-047) |
| DEC-069 | Ảnh gửi: cắt theo khung → cạnh dài **~2400px** (thẻ có QR đọc native) JPEG ~90 |

## 3. Cấu trúc dự án (`android/`)

```text
android/
├── settings.gradle.kts · build.gradle.kts · gradle/libs.versions.toml   (version catalog)
├── vndoc-sdk/            → thư viện AAR công khai
│   └── vn.vndoc.sdk/
│       ├── VNDoc                (điểm vào: configure/scan)
│       ├── config/              ServerConfig, ConfigStore (mã hoá)
│       ├── model/               DocType, FieldValue, ScanResult, ExtractResponse (DTO)
│       ├── network/             OcrApi (Retrofit), OcrClient, ApiError
│       ├── capture/             CameraX + overlay + QualityGate + CaptureScreen (Compose)
│       └── ui/                  ReviewScreen (sửa tay)
└── sample-app/          → app demo dựng trên vndoc-sdk (Settings + luồng đầy đủ)
```

## 4. API công khai

```kotlin
// 1) Cấu hình 1 lần (màn Settings) — lưu mã hoá.
VNDoc.configure(context, ServerConfig(host = "192.168.1.50", port = 11001, apiKey = "…"))

// 2) Quét: mở màn chụp, gọi API, trả kết quả (ActivityResult contract + wrapper suspend).
val result: ScanResult = VNDoc.scan(activity, DocType.CCCD)

sealed interface ScanResult {
  data class Success(val documentType: String, val label: String?,
                     val fields: Map<String, FieldValue>, val overallConfidence: Double,
                     val warnings: List<String>, val rawJson: String) : ScanResult
  data class Retry(val reason: String) : ScanResult          // unknown / confidence thấp
  data class Error(val kind: ErrorKind, val message: String) : ScanResult
}
data class FieldValue(val value: String?, val confidence: Double, val source: String) // source: qr|ocr|structured
enum class ErrorKind { UNAUTHORIZED, FORBIDDEN_IP, BAD_REQUEST, TOO_BUSY, QUALITY_LOW, NETWORK, SERVER }
```

`DocType` (cán bộ chọn) → `docTypeHint`:

| DocType | hint | Ghi chú |
|---|---|---|
| `CMND` | `cmnd` | họ — server detect 9/12 số |
| `CCCD` | `cccd` | họ — server detect chip/2024/mặt |
| `BHYT` | `bhyt` | QR-first |
| `HO_CHIEU` | `passport_vn` | MRZ |
| `DANG_VIEN` | `the_dang_vien` | QR-first (mẫu mới) |
| `QUAN_NHAN` | `the_quan_nhan` | gồm biến thể sĩ quan |
| `GPLX` | `gplx_pet` | |

## 5. Luồng màn hình

```text
[Chọn DocType] → [Camera + overlay khung + quality gate realtime]
   → đạt+ổn định → [TỰ CHỤP] → [cắt+nén] → [POST /extract] → [Review + sửa tay] → trả về
   → kém → gợi ý ("Lại gần / Giữ yên / Tránh loá / Đủ sáng"), chưa chụp
   → lỗi → thông báo thân thiện (401/403/429/mạng) + nút thử lại
```

## 6. Quality gate phía client (thuần Kotlin, không OpenCV)

Đo trên khung `ImageAnalysis` (Y-plane thu nhỏ) — giảm ảnh hỏng gửi lên (server vẫn kiểm FR-002):

| Chỉ số | Cách đo | Ngưỡng khởi điểm |
|---|---|---|
| Độ nét | phương sai gradient (|Δ luma|) | > ngưỡng blur |
| Độ sáng | luma trung bình | [60, 200] |
| Loá | tỉ lệ pixel > 250 | < 5% |
| Lấp khung | tỉ lệ thẻ/khung (theo overlay) | > 80% |
| Ổn định | lệch khung giữa các frame | thấp, giữ N frame |

## 7. Ảnh gửi lên (DEC-069)

- Cắt theo **khung overlay** (bỏ nền) → cạnh dài **~2400px** (đủ nét cho QR nhỏ) → JPEG ~90.
- Giữ orientation đã xoay đúng, **gỡ EXIF GPS**. Mục tiêu < 2–3 MB (server giới hạn 8 MB).
- Server vẫn tự detect+rectify — client cắt thô để tăng độ phân giải phần thẻ.

## 8. Gọi API & map lỗi (khớp DOC-07)

`POST http://<host>:<port>/api/v1/extract` (multipart) — `image`, `docTypeHint` (BẮT BUỘC),
`returnImage=none`; header `X-API-Key`.

| HTTP | ErrorKind / xử lý |
|---|---|
| 200 + `unknown`/confidence thấp | `Retry` — nhắc chụp lại |
| 400 | `BAD_REQUEST` (thiếu/sai hint — lỗi lập trình) |
| 401 | `UNAUTHORIZED` — "Sai API key, kiểm tra cấu hình" |
| 403 | `FORBIDDEN_IP` — "IP thiết bị chưa được cấp phép, báo admin" (whitelist) |
| 413 | ảnh quá lớn — nén lại |
| 422 | `QUALITY_LOW` — "Ảnh quá kém, chụp lại" |
| 429 | `TOO_BUSY` — "Server bận, thử lại" |
| timeout/mạng | `NETWORK` — thử lại 1 lần |

## 9. Cấu hình & kết nối (DEC-066/067)

- Màn Settings: nhập **host, port (mặc định 11001), API key** → lưu `EncryptedSharedPreferences`.
- HTTP cleartext: khai `network_security_config` cho phép cleartext (LAN nội bộ).
- Nút **"Kiểm tra kết nối"** gọi `GET /health` → báo OK / lỗi (sai IP, 403, mất mạng).
- Timeout ~10 s (OCR ~2–3 s, ảnh xoay tới ~5 s) + thử lại 1 lần cho lỗi mạng.

## 10. Riêng tư trên thiết bị (NFR-007)

- Ảnh chỉ ở **cache app**, **xoá** sau khi có kết quả; KHÔNG lưu thư viện ảnh công khai.
- Không gửi dữ liệu đi đâu ngoài server nội bộ đã cấu hình.
- OCR là **hỗ trợ** — cán bộ luôn sửa tay được trước khi lưu (DEC-062).

## 11. Đa mặt (CCCD 2024: trước+sau)

- V1: **1 lần quét = 1 mặt = 1 kết quả**. Luồng ghép trước+sau do **app mẫu** minh hoạ
  (quét mặt trước → nhắc quét mặt sau → gộp field). Không nhồi vào SDK core ở V1.

## 12. Việc tiếp theo (thứ tự)

1. Khung Gradle (version catalog) + 2 module + manifest + network security config.  ← làm trước
2. Core: config (ServerConfig/ConfigStore) · model (DocType/ScanResult/DTO) · network (OcrClient/ApiError).
3. Capture: CameraX + overlay + QualityGate + CaptureScreen (Compose).
4. ReviewScreen (sửa tay) + `VNDoc.scan` (ActivityResult contract).
5. Sample app: Settings + luồng + demo 2 mặt CCCD.
