# Mẫu tham chiếu — CCCD mã vạch (Mặt trước) #01

- **Loại:** `cccd_barcode_front` (DOC-TYPE-002)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** nhãn/regex (KHÔNG để train).
- **Nguồn:** 1 ảnh CCCD mã vạch đời cũ (2016–2020) — 2026-06-29.
- **Lưu ý phân loại:** thẻ ghi **"CĂN CƯỚC CÔNG DÂN"**, số 12 chữ số → đây là **CCCD
  mã vạch**, KHÔNG phải CMND. Phân biệt CCCD gắn chip (có QR mặt trước) vs CCCD
  mã vạch (không QR mặt trước; barcode ở mặt sau, ngoài phạm vi V1 → OCR thuần mặt trước).

## 1. Nhãn & giá trị

| Nhãn | Trường | Giá trị |
|---|---|---|
| `Số` | `idNumber` | 031091006890 |
| `Họ và tên` | `fullName` | NGUYỄN ANH HOÀNG |
| `Ngày, tháng, năm sinh` | `dateOfBirth` | 09/09/1991 → 1991-09-09 |
| `Giới tính` | `sex` | Nam |
| `Quốc tịch` | `nationality` | Việt Nam |
| `Quê quán` | `placeOfOrigin` | Ngũ Phúc, Kiến Thụy, Hải Phòng |
| `Nơi thường trú` | `placeOfResidence` | 1/92 Lê Thánh Tông, Máy Chai, Ngô Quyền, Hải Phòng |
| `Có giá trị đến` | `dateOfExpiry` | 09/09/2031 |

- `Giới tính` và `Quốc tịch` nằm **cùng một hàng** (2 cột).
- `Quê quán`, `Nơi thường trú` **xuống 2 dòng** → gộp dòng.

## 2. JSON kết quả (schema DOC-07)

```json
{
  "documentType": "cccd_barcode_front",
  "documentTypeLabel": "CCCD mã vạch - Mặt trước",
  "fields": {
    "idNumber":         { "value": "031091006890", "confidence": 0.97, "source": "ocr" },
    "fullName":         { "value": "NGUYỄN ANH HOÀNG", "confidence": 0.97, "source": "ocr" },
    "dateOfBirth":      { "value": "1991-09-09", "confidence": 0.98, "source": "ocr", "raw": "09/09/1991" },
    "sex":              { "value": "Nam", "confidence": 0.98, "source": "ocr" },
    "nationality":      { "value": "Việt Nam", "confidence": 0.97, "source": "ocr" },
    "placeOfOrigin":    { "value": "Ngũ Phúc, Kiến Thụy, Hải Phòng", "confidence": 0.92, "source": "ocr" },
    "placeOfResidence": { "value": "1/92 Lê Thánh Tông, Máy Chai, Ngô Quyền, Hải Phòng", "confidence": 0.89, "source": "ocr" },
    "dateOfExpiry":     { "value": "2031-09-09", "confidence": 0.95, "source": "ocr", "raw": "09/09/2031" }
  },
  "structuredDataUsed": [],
  "warnings": [],
  "errors": []
}
```

## 3. Phát hiện ảnh hưởng thiết kế

1. **Mã định danh 12 số, 3 số đầu = mã tỉnh** (031 = Hải Phòng) → có thể **cross-check**
   mã tỉnh với quê quán/nơi thường trú (cảnh báo nếu lệch). Đây là kiểm tra logic miễn phí.
2. Nhãn DOB là **"Ngày, tháng, năm sinh"** (không phải "Ngày sinh") → bổ sung vào `labels`.
3. `Giới tính` + `Quốc tịch` **cùng hàng** → label_anchored xử lý độc lập từng nhãn.
4. `Có giá trị đến` → thêm rule cảnh báo `da_het_han` (thẻ này còn hạn tới 2031).
5. Cùng tập trường với CCCD gắn chip nhưng **thuần OCR** (không QR mặt trước).

## 4. Draft plugin CCCD mã vạch (mặt trước)

```yaml
docType: cccd_barcode_front
displayName: "CCCD mã vạch - Mặt trước"
classify:
  anchors: ["CĂN CƯỚC CÔNG DÂN"]
  signals: [id_digits_eq_12, no_qr_on_front]   # phân biệt với CCCD gắn chip (có QR)
extraction:
  strategy: label_anchored
  fields:
    - name: idNumber
      labels: ["Số"]
      take: right_of_label
      type: digits
      normalize: [removeSpaces, fixDigits]
      validate: { regex: '^\d{12}$' }
      crossCheckProvince: true        # 3 số đầu vs tỉnh trong địa chỉ
    - name: fullName
      labels: ["Họ và tên"]
      take: below_label
      type: text_vi
    - name: dateOfBirth
      labels: ["Ngày, tháng, năm sinh", "Ngày sinh"]
      take: date_after_label
      type: date
    - name: sex
      labels: ["Giới tính"]
      take: right_of_label
      type: sex
    - name: nationality
      labels: ["Quốc tịch"]
      take: right_of_label
      type: text_vi
    - name: placeOfOrigin
      labels: ["Quê quán"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, dictFix]
    - name: placeOfResidence
      labels: ["Nơi thường trú"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, dictFix]
    - name: dateOfExpiry
      labels: ["Có giá trị đến"]
      take: date_after_label
      type: date
      checks: [warn_if_expired]
```
