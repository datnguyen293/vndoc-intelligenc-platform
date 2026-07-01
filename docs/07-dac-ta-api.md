# DOC-07 — Đặc tả API

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-03
- **Truy vết:** FR-001, FR-014, FR-015, FR-019, FR-020, NFR-005, NFR-007

## 1. Nguyên tắc

- REST trên HTTP, chạy trong **mạng nội bộ**, offline.
- Upload ảnh bằng **`multipart/form-data`** (ảnh nhị phân; nhẹ hơn base64 ~33%).
- Output luôn là **JSON thống nhất** một schema cho mọi loại giấy tờ.
- API **stateless**; mỗi request xử lý một ảnh/một mặt giấy tờ.
- Bảo mật nội bộ: tuỳ chọn **API key** qua header và HTTPS nội bộ (NFR-007).

## 2. Base URL & xác thực
```text
Base URL: http://<windows-host>:8080/api/v1
Header (tuỳ chọn): X-API-Key: <khóa chia sẻ cấu hình trong service>
```

## 3. Danh sách endpoint

| Mã | Method | Path | Mục đích |
|---|---|---|---|
| API-001 | POST | `/extract` | Bóc tách 1 ảnh giấy tờ → JSON |
| API-002 | GET | `/doctypes` | Danh sách loại giấy tờ hỗ trợ |
| API-003 | GET | `/health` | Trạng thái service (sống/model warm) |
| API-004 | GET | `/version` | Phiên bản service & plugin |

---

## 4. API-001 — POST `/extract`

### 4.1 Request (`multipart/form-data`)

| Part | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `image` | file (JPEG/PNG) | có | Ảnh mặt trước giấy tờ |
| `docTypeHint` | text | **CÓ** (DEC-047) | Loại giấy tờ cán bộ chọn trên app: **họ thô** `cmnd`/`cccd` (hệ thống tự detect loại con — DOC-05 §2.3) **hoặc** docType cụ thể (vd `the_dang_vien`, `bhyt`, `passport_vn`). Thiếu / không hợp lệ → `400 invalid_request`. Phân loại dựa hint là chính, KHÔNG đoán mù. |
| `returnImage` | text (`none`\|`rectified`\|`annotated`) | không | Có trả ảnh xử lý kèm không (mặc định `none`) |
| `options` | text (JSON) | không | Cấu hình thêm (vd `{"minConfidence":0.5}`) |

Giới hạn: kích thước ảnh tối đa cấu hình được (mặc định 8 MB). Vượt → `413`.

### 4.2 Response 200 — JSON thống nhất

```json
{
  "requestId": "b1c2d3e4-...",
  "documentType": "cccd_chip_front",
  "documentTypeLabel": "CCCD gắn chip - Mặt trước",
  "classificationConfidence": 0.98,
  "processingTimeMs": 312,
  "fields": {
    "idNumber":        { "value": "012345678901", "confidence": 0.99, "source": "structured" },
    "fullName":        { "value": "NGUYỄN VĂN A", "confidence": 0.97, "source": "structured" },
    "dateOfBirth":     { "value": "1990-05-12",   "confidence": 0.98, "source": "structured", "raw": "12/05/1990" },
    "sex":             { "value": "Nam",          "confidence": 0.99, "source": "structured" },
    "nationality":     { "value": "Việt Nam",     "confidence": 0.95, "source": "ocr" },
    "placeOfOrigin":   { "value": "Hà Nội",       "confidence": 0.90, "source": "ocr" },
    "placeOfResidence":{ "value": "Số 1, P. X, Q. Y, Hà Nội", "confidence": 0.88, "source": "ocr" },
    "dateOfExpiry":    { "value": "2030-05-12",   "confidence": 0.93, "source": "ocr", "raw": "12/05/2030" }
  },
  "overallConfidence": 0.95,
  "structuredDataUsed": ["qr"],
  "warnings": [],
  "errors": [],
  "image": null
}
```

**Quy ước field object:**
| Khóa | Ý nghĩa |
|---|---|
| `value` | giá trị đã chuẩn hóa |
| `confidence` | [0..1] |
| `source` | `structured` (QR/MRZ/barcode) hoặc `ocr` |
| `raw` | (tuỳ chọn) giá trị thô trước chuẩn hóa |

- Trường thiếu/không đọc được: **không bỏ khóa**, đặt `value: null`, `confidence: 0`,
  thêm cảnh báo tương ứng → schema nhất quán (NFR-005).
- Nếu `returnImage != none`: `image` = `{ "format":"jpeg", "base64":"...", "kind":"rectified" }`.

### 4.3 Response khi không nhận dạng được loại
```json
{
  "requestId": "...",
  "documentType": "unknown",
  "processingTimeMs": 120,
  "fields": {},
  "warnings": ["khong_nhan_dang_duoc_loai"],
  "errors": []
}
```

### 4.4 Mã lỗi
| HTTP | code (body) | Khi nào |
|---|---|---|
| 200 | — | Thành công (kể cả `unknown`) |
| 400 | `invalid_request` | thiếu `image`, sai định dạng |
| 401 | `unauthorized` | sai/thiếu API key (nếu bật) |
| 413 | `image_too_large` | ảnh vượt giới hạn |
| 422 | `image_quality_too_low` | ảnh quá mờ/loá (FR-002) |
| 429 | `too_busy` | quá tải, hàng đợi đầy (xem DOC-10) |
| 500 | `internal_error` | lỗi không lường trước |

Body lỗi:
```json
{ "requestId": "...", "error": { "code": "image_quality_too_low",
  "message": "Ảnh quá mờ", "details": { "blurScore": 12.3 } } }
```

---

## 5. API-002 — GET `/doctypes`
```json
{ "docTypes": [
  { "code": "cccd_chip_front", "label": "CCCD gắn chip - Mặt trước", "ready": true },
  { "code": "the_quan_nhan", "label": "Thẻ quân nhân", "ready": false }
] }
```
- `ready=false`: plugin tồn tại nhưng chưa có ROI map (chờ ảnh mẫu).

## 6. API-003 — GET `/health`
```json
{ "status": "ok", "modelsWarm": true, "uptimeSec": 38211, "queueDepth": 0 }
```

## 7. API-004 — GET `/version`
```json
{ "service": "1.0.0", "engine": { "detect": "PaddleOCR-DB", "recognize": "VietOCR" },
  "plugins": { "cccd_chip_front": "1.0", "passport_vn": "1.0" } }
```

---

## 8. Quy ước chung
- Charset UTF-8; mọi text tiếng Việt **có dấu**.
- Thời gian theo ISO-8601; ngày `YYYY-MM-DD`.
- `requestId` do service sinh (UUID), trả lại để truy vết log.
- Không trả ảnh gốc; chỉ trả ảnh xử lý khi client yêu cầu (NFR-007).

## 9. Quyết định khóa
| ID | Quyết định |
|---|---|
| DEC-040 | Upload ảnh bằng multipart/form-data |
| DEC-041 | Một response schema cho mọi loại; field thiếu = value null |
| DEC-042 | API stateless, 1 request = 1 ảnh = 1 mặt |
| DEC-043 | `unknown` vẫn trả HTTP 200 với cảnh báo, không phải lỗi |
| DEC-047 | `docTypeHint` **BẮT BUỘC** (cán bộ luôn chọn loại/họ trên app); thiếu/không hợp lệ → `400`. Phân loại dựa hint là chính, không đoán mù. |
