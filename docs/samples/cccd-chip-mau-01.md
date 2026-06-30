# Mẫu tham chiếu — CCCD gắn chip (Mặt trước) #01

- **Loại:** `cccd_chip_front` (DOC-TYPE-001)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** nhãn + chốt parser QR (KHÔNG để train).
- **Nguồn:** 1 ảnh CCCD gắn chip mặt trước — 2026-06-29.

## 1. Quan sát căn chỉnh

- Thẻ ngang (ID-1), nền hoa văn trống đồng + bản đồ VN, chữ tiêu đề đỏ.
- **Mã QR ở góc trên bên phải MẶT TRƯỚC** (xác nhận chiến lược structured-data-first).
- Biểu tượng **chip** cạnh dòng "Citizen Identity Card".
- Nhãn **song ngữ Việt/Anh**, bố cục nhãn–giá trị; `Giới tính`+`Quốc tịch` cùng hàng.

## 2. Nhãn & giá trị (vùng nhìn)

| Nhãn (VN / EN) | Trường | Giá trị |
|---|---|---|
| Số / No. | `idNumber` | 024088010438 |
| Họ và tên / Full name | `fullName` | NGUYỄN TIẾN ĐẠT |
| Ngày sinh / Date of birth | `dateOfBirth` | 29/03/1988 |
| Giới tính / Sex | `sex` | Nam |
| Quốc tịch / Nationality | `nationality` | Việt Nam |
| Quê quán / Place of origin | `placeOfOrigin` | Lam Cốt, Tân Yên, Bắc Giang |
| Nơi thường trú / Place of residence | `placeOfResidence` | Lam Cốt, Tân Yên, Bắc Giang |
| Có giá trị đến / Date of expiry | `dateOfExpiry` | 29/03/2028 |

## 3. Mã QR — định dạng parser `cccd_qr` (CHỐT)

Chuỗi QR gồm **7 trường**, ngăn cách bằng ký tự `|`:

```
<Số CCCD> | <Số CMND 9 số cũ> | <Họ và tên> | <Ngày sinh ddMMyyyy> | <Giới tính> | <Nơi thường trú> | <Ngày cấp ddMMyyyy>
```

Ví dụ (suy ra cho mẫu này; số CMND cũ lấy từ giấy tờ cũ cùng người):
```
024088010438|121647952|Nguyễn Tiến Đạt|29031988|Nam|Lam Cốt, Tân Yên, Bắc Giang|...
```

**QR `mapsTo`:** `idNumber, oldIdNumber, fullName, dateOfBirth, sex, placeOfResidence, dateOfIssue`.

Lưu ý quan trọng về QR:
- QR **không chứa**: `nationality` (luôn Việt Nam), `placeOfOrigin` (quê quán),
  `dateOfExpiry` → các trường này **chỉ lấy bằng OCR**.
- QR **chứa** `dateOfIssue` (ngày cấp) — vốn **không in trên mặt trước** → QR là
  nguồn duy nhất cho ngày cấp.
- QR có `oldIdNumber` (số CMND 9 số cũ) — hữu ích để liên kết hồ sơ cũ.

## 4. JSON kết quả (schema DOC-07)

```json
{
  "documentType": "cccd_chip_front",
  "documentTypeLabel": "CCCD gắn chip - Mặt trước",
  "fields": {
    "idNumber":         { "value": "024088010438", "confidence": 0.99, "source": "structured" },
    "oldIdNumber":      { "value": "121647952", "confidence": 0.99, "source": "structured" },
    "fullName":         { "value": "NGUYỄN TIẾN ĐẠT", "confidence": 0.98, "source": "structured" },
    "dateOfBirth":      { "value": "1988-03-29", "confidence": 0.99, "source": "structured", "raw": "29/03/1988" },
    "sex":              { "value": "Nam", "confidence": 0.99, "source": "structured" },
    "nationality":      { "value": "Việt Nam", "confidence": 0.97, "source": "ocr" },
    "placeOfOrigin":    { "value": "Lam Cốt, Tân Yên, Bắc Giang", "confidence": 0.93, "source": "ocr" },
    "placeOfResidence": { "value": "Lam Cốt, Tân Yên, Bắc Giang", "confidence": 0.94, "source": "structured" },
    "dateOfIssue":      { "value": null, "confidence": 0.0, "source": "structured" },
    "dateOfExpiry":     { "value": "2028-03-29", "confidence": 0.96, "source": "ocr", "raw": "29/03/2028" }
  },
  "structuredDataUsed": ["qr"],
  "warnings": [],
  "errors": []
}
```
> `dateOfIssue` sẽ có giá trị khi đọc QR thật (em đọc bằng mắt nên để null).

## 5. Phát hiện ảnh hưởng thiết kế

1. **QR mặt trước** → structured-data-first xác nhận; chốt parser `cccd_qr` 7 trường.
2. **QR thiếu quê quán + hạn dùng** → 2 trường này luôn cần OCR (đừng giả định QR đủ).
3. **QR có ngày cấp** (không in trên mặt) → đừng bỏ; là nguồn duy nhất.
4. **Mã tỉnh = 3 số đầu** (024 = Bắc Giang) → cross-check với quê quán/thường trú.
5. Phân biệt với CCCD mã vạch: **có QR mặt trước** (gắn chip) vs không (mã vạch).
6. Số CCCD = `personalIdNumber` trên hộ chiếu mới → có thể liên kết chéo giấy tờ.

## 6. Draft plugin CCCD gắn chip (QR-first + label-anchored)

```yaml
docType: cccd_chip_front
displayName: "CCCD gắn chip - Mặt trước"
classify:
  anchors: ["CĂN CƯỚC CÔNG DÂN", "Citizen Identity Card"]
  signals: [has_qr_top_right]
structuredData:
  - kind: qr
    roi: { x: 1300, y: 60, w: 230, h: 230 }   # góc trên phải (toạ độ template chuẩn)
    parser: cccd_qr
    mapsTo: [idNumber, oldIdNumber, fullName, dateOfBirth, sex, placeOfResidence, dateOfIssue]
extraction:
  strategy: label_anchored
  fields:
    - name: idNumber
      labels: ["Số", "No."]
      take: right_of_label
      source: [structured, ocr]
      type: digits
      validate: { regex: '^\d{12}$' }
      crossCheckProvince: true
    - name: fullName
      labels: ["Họ và tên", "Full name"]
      take: below_label
      source: [structured, ocr]
      type: text_vi
    - name: dateOfBirth
      labels: ["Ngày sinh", "Date of birth"]
      take: date_after_label
      source: [structured, ocr]
      type: date
    - name: sex
      labels: ["Giới tính", "Sex"]
      take: right_of_label
      source: [structured, ocr]
      type: sex
    - name: nationality
      labels: ["Quốc tịch", "Nationality"]
      take: right_of_label
      type: text_vi
    - name: placeOfOrigin
      labels: ["Quê quán", "Place of origin"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, dictFix]
    - name: placeOfResidence
      labels: ["Nơi thường trú", "Place of residence"]
      take: right_of_label_or_below
      source: [structured, ocr]
      type: text_vi
      normalize: [collapseSpaces, dictFix]
    - name: dateOfExpiry
      labels: ["Có giá trị đến", "Date of expiry"]
      take: date_after_label
      type: date
      checks: [warn_if_expired]
    - name: dateOfIssue
      source: [structured]      # chỉ từ QR
      type: date
      required: false
    - name: oldIdNumber
      source: [structured]      # chỉ từ QR
      type: digits
      validate: { regex: '^\d{9}$' }
      required: false
```
