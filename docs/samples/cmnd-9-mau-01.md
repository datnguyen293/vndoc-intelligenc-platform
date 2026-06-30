# Mẫu tham chiếu — CMND 9 số #01

- **Loại:** `cmnd_9` (DOC-TYPE-003)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** nhãn/regex (KHÔNG để train).
- **Nguồn:** 1 ảnh CMND 9 số (ép plastic, đã cũ) — 2026-06-29.

## 1. Quan sát căn chỉnh

- Thẻ ngang, ép plastic, nền hoa văn xanh, **dấu nổi (con dấu giáp lai) đè lên số**.
- Bố cục: quốc huy + ảnh chân dung bên trái; tiêu đề + cột nhãn–giá trị bên phải.
- Nhãn theo sau là **đường gạch chấm (····)**, giá trị nằm trên đường chấm.

## 2. Nhãn & giá trị

| Nhãn | Trường | Giá trị |
|---|---|---|
| `Số` | `idNumber` | 121647952 |
| `Họ tên` | `fullName` | NGUYỄN TIẾN ĐẠT |
| `Sinh ngày` | `dateOfBirth` | 29-03-1988 → 1988-03-29 |
| `Nguyên quán` | `placeOfOrigin` | Lam Cốt, Tân Yên, Bắc Giang |
| `Nơi ĐKHK thường trú` | `placeOfResidence` | Tân Lập, Lam Cốt, Tân Yên, Bắc Giang |

> Mặt trước CMND 9 số **không có** giới tính, quốc tịch, ngày cấp, hạn dùng.

## 3. JSON kết quả (schema DOC-07)

```json
{
  "documentType": "cmnd_9",
  "documentTypeLabel": "CMND 09 số",
  "fields": {
    "idNumber":         { "value": "121647952", "confidence": 0.86, "source": "ocr" },
    "fullName":         { "value": "NGUYỄN TIẾN ĐẠT", "confidence": 0.95, "source": "ocr" },
    "dateOfBirth":      { "value": "1988-03-29", "confidence": 0.96, "source": "ocr", "raw": "29-03-1988" },
    "placeOfOrigin":    { "value": "Lam Cốt, Tân Yên, Bắc Giang", "confidence": 0.88, "source": "ocr" },
    "placeOfResidence": { "value": "Tân Lập, Lam Cốt, Tân Yên, Bắc Giang", "confidence": 0.85, "source": "ocr" }
  },
  "structuredDataUsed": [],
  "warnings": ["so_in_do_de_len_dau_giap_lai"],
  "errors": []
}
```

## 4. Phát hiện ảnh hưởng thiết kế

1. **Số CMND in màu đỏ, đè dấu giáp lai** → tương phản kém, OCR dễ sai số → confidence
   thấp, **không có checksum** để tự sửa. Cần: tăng tương phản kênh đỏ ở ROI số, ràng
   buộc `^\d{9}$`, và cho phép cán bộ sửa tay.
2. **Đường gạch chấm dưới giá trị** → bộ OCR/hậu xử lý phải **bỏ ký tự chấm thừa**.
3. **Địa chỉ (Nguyên quán, thường trú) xuống 2 dòng** → gộp dòng kế tiếp.
4. Ngày dạng `dd-MM-yyyy`; một số CMND 9 số đời rất cũ chỉ ghi **năm sinh** → cho phép
   `partialDate` (thẻ này có đủ ngày).
5. Thẻ cũ/mòn/ép plastic loá → quality gate (DOC-09) cần khoan dung hơn loại mới.

## 5. Draft plugin CMND 9 số

```yaml
docType: cmnd_9
displayName: "CMND 09 số"
classify:
  anchors: ["GIẤY CHỨNG MINH NHÂN DÂN", "CHỨNG MINH NHÂN DÂN"]
  signals: [id_digits_eq_9]
extraction:
  strategy: label_anchored
  preprocess: [boost_red_channel_for_id]
  fields:
    - name: idNumber
      labels: ["Số"]
      take: right_of_label
      type: digits
      normalize: [removeSpaces, fixDigits, stripDots]
      validate: { regex: '^\d{9}$' }
    - name: fullName
      labels: ["Họ tên", "Họ và tên"]
      take: right_of_label
      type: text_vi
    - name: dateOfBirth
      labels: ["Sinh ngày"]
      take: date_after_label
      type: date
    - name: placeOfOrigin
      labels: ["Nguyên quán"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, stripDots, dictFix]
    - name: placeOfResidence
      labels: ["Nơi ĐKHK thường trú", "Nơi đăng ký hộ khẩu thường trú"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, stripDots, dictFix]
```
