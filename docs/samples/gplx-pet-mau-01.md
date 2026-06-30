# Mẫu tham chiếu — GPLX PET (3 thẻ)

- **Loại:** `gplx_pet` (DOC-TYPE-005)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** nhãn/regex/enum (KHÔNG để train).
- **Nguồn:** 3 ảnh GPLX PET (hạng B2 / B1 / D) — 2026-06-29.

## 1. Quan sát chung

- Thẻ ngang (ID-1), nền vàng hoa văn, tiêu đề đỏ "GIẤY PHÉP LÁI XE / DRIVER'S LICENSE".
- Góc trên trái: "BỘ GTVT / MOT". Ảnh chân dung trái; cột nhãn–giá trị phải.
- Nhãn **song ngữ Việt/Anh** (dấu `/`). **Không có QR** trên các thẻ này → thuần OCR.
- Dấu mộc đỏ + chữ ký đè lên vùng dưới (nơi cấp, ngày cấp) → có thể nhiễu OCR.

## 2. Nhãn & giá trị (3 thẻ)

| Nhãn (VN / EN) | Trường | Thẻ #1 | Thẻ #2 | Thẻ #3 |
|---|---|---|---|---|
| Số / No. | `idNumber` | 010114000119 | 990170000806 | 010103033708 |
| Họ tên / Full name | `fullName` | LÂM TRỌNG GIANG | *(mờ)* | NGUYỄN ĐÌNH TÙNG |
| Ngày sinh / Date of Birth | `dateOfBirth` | 16/01/1988 | 25/12/1992 | 15/02/1988 |
| Quốc tịch / Nationality | `nationality` | VIỆT NAM | VIỆT NAM | VIỆT NAM |
| Nơi cư trú / Address | `placeOfResidence` | P. Đức Giang, Q. Long Biên, TP. Hà Nội | P. Đông Sơn, TP. Thanh Hóa, T. Thanh Hóa | X. Hoàng Diệu, H. Chương Mỹ, TP. Hà Nội |
| (câu) ngày…tháng…năm | `dateOfIssue` | 19/12/2012 | 20/02/2017 | 14/11/2017 |
| Hạng / Class | `licenseClass` | B2 | B1 | D |
| Có giá trị đến / Expires | `dateOfExpiry` | 19/12/2022 | 25/12/2052 | 14/11/2022 |

> Thẻ #2 là ảnh công khai bị che tên → minh hoạ trường hợp `fullName` đọc lỗi/thiếu.

## 3. JSON kết quả (thẻ #1, schema DOC-07)

```json
{
  "documentType": "gplx_pet",
  "documentTypeLabel": "GPLX PET",
  "fields": {
    "idNumber":         { "value": "010114000119", "confidence": 0.97, "source": "ocr" },
    "fullName":         { "value": "LÂM TRỌNG GIANG", "confidence": 0.96, "source": "ocr" },
    "dateOfBirth":      { "value": "1988-01-16", "confidence": 0.97, "source": "ocr", "raw": "16/01/1988" },
    "nationality":      { "value": "Việt Nam", "confidence": 0.97, "source": "ocr" },
    "placeOfResidence": { "value": "P. Đức Giang, Q. Long Biên, TP. Hà Nội", "confidence": 0.90, "source": "ocr" },
    "licenseClass":     { "value": "B2", "confidence": 0.96, "source": "ocr" },
    "dateOfIssue":      { "value": "2012-12-19", "confidence": 0.88, "source": "ocr", "raw": "ngày 19 tháng 12 năm 2012" },
    "dateOfExpiry":     { "value": "2022-12-19", "confidence": 0.95, "source": "ocr", "raw": "19/12/2022" }
  },
  "structuredDataUsed": [],
  "warnings": ["da_het_han"],
  "errors": []
}
```

## 4. Phát hiện ảnh hưởng thiết kế

1. **Số GPLX 12 số** (2 số đầu = mã tỉnh cấp) → regex `^\d{12}$`.
2. **Ngày cấp dạng câu** "[Nơi cấp], ngày DD tháng MM năm YYYY" → parser `vn_date_phrase`;
   có thể tách thêm `issuePlace` (Hà Nội / Hưng Yên...) đứng trước "ngày".
3. **Hạng (Class)** là enum: `A1, A2, A3, A4, B1, B2, C, D, E, FB2, FC, FD, FE` →
   validate theo tập; là trường nghiệp vụ quan trọng (xác định loại xe được lái).
4. **Hạn dùng biến thiên lớn**: B1 tới 2052 (theo tuổi), B2/C/D ~5–10 năm → `warn_if_expired`
   (nhiều thẻ mẫu đã hết hạn 2022).
5. **Dấu mộc + chữ ký đè** vùng dưới → ROI ngày cấp/nơi cấp nhiễu; ưu tiên đọc
   `dateOfExpiry` (rõ, không bị đè) làm trường chắc.
6. **Không QR** ở các thẻ này → `gplx_pet` mặc định OCR; vẫn để ngỏ `structuredData: qr`
   cho bản mới có QR.

## 5. Draft plugin GPLX PET

```yaml
docType: gplx_pet
displayName: "GPLX PET"
classify:
  anchors: ["GIẤY PHÉP LÁI XE", "DRIVER'S LICENSE"]
extraction:
  strategy: label_anchored
  fields:
    - name: idNumber
      labels: ["Số", "No."]
      take: right_of_label
      type: digits
      normalize: [removeSpaces, fixDigits]
      validate: { regex: '^\d{12}$' }
    - name: fullName
      labels: ["Họ tên", "Full name"]
      take: right_of_label
      type: text_vi
    - name: dateOfBirth
      labels: ["Ngày sinh", "Date of Birth"]
      take: date_after_label
      type: date
    - name: nationality
      labels: ["Quốc tịch", "Nationality"]
      take: right_of_label
      type: text_vi
    - name: placeOfResidence
      labels: ["Nơi cư trú", "Address"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, dictFix]
    - name: licenseClass
      labels: ["Hạng", "Class"]
      take: right_of_label
      type: enum
      validate: { enum: [A1, A2, A3, A4, B1, B2, C, D, E, FB2, FC, FD, FE] }
    - name: dateOfIssue
      labels: ["ngày", "tháng", "năm"]
      take: vn_date_phrase
      type: date
      required: false
    - name: dateOfExpiry
      labels: ["Có giá trị đến", "Expires"]
      take: date_after_label
      type: date
      checks: [warn_if_expired]
```
