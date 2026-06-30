# DOC-03 — Kiến trúc tổng thể

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-00, DOC-01, DOC-02

## 1. Mục đích

Mô tả kiến trúc phần mềm tổng thể: thành phần, ranh giới, phụ thuộc, luồng xử lý
và nguyên tắc thiết kế. Quyết định công nghệ cụ thể nằm ở DOC-04.

## 2. Sơ đồ ngữ cảnh (C4 — Context)

```text
┌─────────────────┐     HTTP/JSON (LAN)    ┌──────────────────────────────┐
│  Thiết bị Android │ ───────────────────▶ │  OCR Service (Windows, offline) │
│  - Chụp ảnh       │ ◀─────────────────── │  - Bóc tách → JSON              │
│  - Hiển thị KQ    │     JSON kết quả      │                                │
└─────────────────┘                        └──────────────────────────────┘
```

- Android: capture, quality gate phía client, gửi ảnh, hiển thị kết quả, cho phép
  sửa tay. **Không** chứa logic OCR.
- OCR Service: toàn bộ xử lý ảnh, đọc dữ liệu máy đọc, OCR, validate, sinh JSON.

## 3. Thành phần bên trong OCR Service (C4 — Container/Component)

```text
                    ┌────────────────────── OCR Service ──────────────────────┐
   HTTP request ──▶ │ [1] API Layer (FastAPI)                                  │
                    │        │                                                 │
                    │        ▼                                                 │
                    │ [2] Pipeline Engine (điều phối stage, đo thời gian)       │
                    │   ├─ [3] Image Quality Check                             │
                    │   ├─ [4] Document Detection (classical CV)               │
                    │   ├─ [5] Perspective Rectification                       │
                    │   ├─ [6] Document Classification (thuần luật, tín hiệu cứng) │
                    │   ├─ [7] Plugin Manager  ──▶ Plugin Registry (YAML)      │
                    │   ├─ [8] Structured-Data Reader (QR / MRZ / barcode)     │
                    │   ├─ [9] OCR Engine (PaddleOCR det + VietOCR rec)        │
                    │   ├─ [10] Validation & Normalization Engine              │
                    │   └─ [11] Response Builder                               │
                    │        │                                                 │
                    │        ▼                                                 │
   JSON response ◀─ │ [12] Logging / Metrics                                   │
                    │ [13] Model Runtime Pool (OpenVINO/ONNX, warm, CPU)       │
                    └─────────────────────────────────────────────────────────┘
```

## 4. Vai trò từng thành phần

| # | Thành phần | Trách nhiệm | Không làm |
|---|---|---|---|
| 1 | API Layer | Nhận HTTP, validate cấu trúc request, mã lỗi chuẩn | Không chứa logic OCR |
| 2 | Pipeline Engine | Điều phối stage, tạo context, đo thời gian, gom warning/error | Không biết chi tiết loại giấy tờ |
| 3 | Image Quality Check | Chấm điểm mờ/sáng/nghiêng; quyết định reject sớm | Không sửa ảnh nặng |
| 4 | Document Detection | Tìm khung giấy tờ (contour) → polygon | Không phân loại |
| 5 | Rectification | Warp phối cảnh về template chuẩn | — |
| 6 | Classification | Xác định `DOC-TYPE` + confidence | Không đọc field |
| 7 | Plugin Manager | Load plugin theo type, cấp ROI map/validator/dictionary | Không OCR |
| 8 | Structured-Data Reader | Đọc QR/MRZ/barcode, parse ra field | Không OCR text tự do |
| 9 | OCR Engine | Detect dòng + recognize tiếng Việt theo ROI | Không validate |
| 10 | Validation/Normalization | Regex, checksum, chuẩn hóa, cross-check, confidence | Không biết HTTP |
| 11 | Response Builder | Gom thành JSON thống nhất | — |
| 12 | Logging/Metrics | Log request, thời gian, lỗi (mask dữ liệu nhạy cảm) | — |
| 13 | Model Runtime Pool | Giữ model warm, chia sẻ giữa request, giới hạn concurrency | — |

## 5. Luồng xử lý chính

```text
1. Nhận request (ảnh + options)
2. Quality check ──(quá kém)──▶ trả warning "chụp lại", dừng
3. Document detection → polygon khung
4. Perspective rectification → ảnh template chuẩn
5. Classification → DOC-TYPE (hoặc unknown → dừng có thông báo)
6. Plugin Manager nạp plugin theo DOC-TYPE
7. Structured-Data Reader: thử QR/MRZ/barcode (nếu plugin khai báo có)
8. OCR Engine: OCR các ROI mà bước 7 chưa cấp giá trị
9. Validation + Normalization + cross-check (nguồn QR ưu tiên hơn OCR)
10. Tính confidence từng trường + tổng
11. Response Builder → JSON (+ ảnh xử lý nếu yêu cầu)
12. Ghi log + metrics
```

## 6. Trạng thái trung gian (Processing Context)

Pipeline truyền một `ProcessingContext` qua các stage, chứa:

- `requestId`, metadata request, options
- `imageOriginal`, `imageRectified`
- `documentPolygon`, `documentType`, `classificationConfidence`
- `structuredData` (kết quả QR/MRZ/barcode)
- `roiCrops`, `ocrResults`
- `fields` (sau validate/normalize), `warnings`, `errors`
- `timings` (mốc thời gian từng stage)

## 7. Nguyên tắc kiến trúc

1. Android không làm OCR.
2. API **stateless** (mỗi request độc lập; phiên ghép 2 mặt là tuỳ chọn tầng trên).
3. Core engine không biết chi tiết từng loại giấy tờ — chỉ làm việc qua plugin contract.
4. Mỗi loại giấy tờ = một plugin.
5. Mọi output đi qua một response model thống nhất.
6. Module nào việc nấy; không chồng lấn trách nhiệm.
7. Cấu hình và plugin nằm ngoài mã nguồn core.
8. **Structured-data ưu tiên hơn OCR** khi cùng một trường có nhiều nguồn.
9. Model runtime phải thay thế được (OCR engine không khóa cứng vào API).

## 8. Quy tắc phụ thuộc

```text
API Layer ──▶ Pipeline Engine ──▶ Core abstractions (interfaces)
Plugin ──▶ Plugin contract  (KHÔNG phụ thuộc ngược vào Core)
OCR Engine / Structured Reader ──▶ Model Runtime Pool
Validation ──▶ nhận dữ liệu từ Plugin + OCR; KHÔNG đọc UI/HTTP
```

- Phụ thuộc luôn hướng vào trong (Clean Architecture).
- OCR engine và Structured Reader đứng sau interface để thay thế được.

## 9. Mô hình triển khai

- Chạy trên Windows 10/11 / Windows Server, đóng gói **Windows Service**.
- Một process giữ Model Runtime Pool warm; phục vụ request qua FastAPI + worker.
- Plugin và model tách thành thư mục riêng (`/plugins`, `/models`, `/config`).
- Chi tiết concurrency, đóng gói, benchmark ở DOC-10.

## 10. Điểm mở (sẽ khóa ở tài liệu con)

| Điểm | Tài liệu khóa |
|---|---|
| Lựa chọn công nghệ cụ thể (framework, runtime, engine) | DOC-04 |
| Cơ chế phân loại + format manifest plugin | DOC-05 |
| Thuật toán đọc QR/MRZ/barcode + ngân sách thời gian | DOC-06 |
| Hợp đồng API chi tiết | DOC-07 |
| Chiến lược concurrency, cache, đóng gói service | DOC-10 |
