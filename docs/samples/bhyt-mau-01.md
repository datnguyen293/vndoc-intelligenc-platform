# Mẫu tham chiếu — Thẻ BHYT #01

- **Loại:** `bhyt` (DOC-TYPE-006)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** nhãn/regex/ROI (KHÔNG dùng để train).
- **Nguồn:** 1 ảnh thẻ BHYT do người dùng cung cấp (2026-06-29).

## 1. Quan sát căn chỉnh (rectification)

- Ảnh gốc **xoay 90°** (chữ chạy dọc cạnh phải) → pipeline phải tự phát hiện hướng
  và xoay về phương ngang trước khi OCR (xem bổ sung S3 ở DOC-06).
- Sau khi xoay đúng chiều, bố cục:
  - Trên cùng: header xanh "BẢO HIỂM XÃ HỘI VIỆT NAM" + tiêu đề đỏ "THẺ BẢO HIỂM Y TẾ".
  - Trái: ô ảnh trống (khung) + **mã QR**.
  - Phải: cột nhãn–giá trị (các trường chính).
  - Dưới: nơi cấp/đổi, ngày cấp, chức danh ký, chữ ký, dấu tròn đỏ.

## 2. Nhãn in trên thẻ (verbatim — gồm viết tắt)

| Nhãn | Trường | Ghi chú |
|---|---|---|
| `Mã số:` | `idNumber` | 10 chữ số (mẫu mới 2021) |
| `Họ và tên:` | `fullName` | |
| `Ngày sinh:` | `dateOfBirth` | dd/MM/yyyy |
| `Giới tính:` | `sex` | Nam/Nữ |
| (số cạnh giới tính, trong ô) | `benefitLevel` | mức hưởng 1–5 |
| `Nơi ĐK KCB BĐ:` | `registeredHospital` | = "Nơi đăng ký khám chữa bệnh ban đầu" |
| `Giá trị sử dụng: từ ngày` | `validFrom` | |
| `Thời điểm đủ 05 năm liên tục: từ ngày` | `fiveYearContinuous` | có thể không có ở 1 số thẻ |
| `Nơi cấp, đổi thẻ BHYT:` | `issuePlace` | |
| `Ngày … tháng … năm` | `dateOfIssue` | ngày cấp thẻ |
| `Mã:` | `objectCode` | mã đối tượng (vd 01-C54…) |

## 3. Giá trị mẫu (ground truth do người đọc bằng mắt)

| Trường | Giá trị | Chuẩn hóa |
|---|---|---|
| idNumber | 0111077012 | 0111077012 |
| fullName | NGUYỄN TIẾN ĐẠT | NGUYỄN TIẾN ĐẠT |
| dateOfBirth | 29/03/1988 | 1988-03-29 |
| sex | Nam | Nam |
| benefitLevel | 4 | 4 |
| registeredHospital | Trạm y tế phường Láng Thượng (TTYT Đống Đa) | (dictFix) |
| validFrom | 01/07/2023 | 2023-07-01 |
| fiveYearContinuous | 01/10/2027 | 2027-10-01 |
| issuePlace | Quận Cầu Giấy, Thành phố Hà Nội | — |
| dateOfIssue | 31/07/2023 | 2023-07-31 |
| objectCode | 01-C54… (bị cắt mép ảnh) | — |

> Đây là dữ liệu cá nhân thật — chỉ dùng nội bộ để hiệu chỉnh, không phát tán.

## 4. Phát hiện ảnh hưởng thiết kế

1. **Hướng ảnh:** cần bước chuẩn hóa xoay 0/90/180/270° (PaddleOCR angle cls) → DOC-06 S3.
2. **Mã số 10 số** (không phải 15 ký tự) → sửa regex BHYT trong DOC-08.
3. **Có QR trên mặt thông tin** → BHYT dùng structured-data-first (QR là nguồn chuẩn).
4. **Không có trường "Địa chỉ"** ở mẫu mới → bỏ `placeOfResidence`, thêm `issuePlace`,
   `benefitLevel`, `objectCode`.
5. **Nhãn viết tắt** ("Nơi ĐK KCB BĐ") → manifest khớp cả viết tắt lẫn đầy đủ.

## 5. Draft plugin BHYT (bám nhãn + QR)

```yaml
docType: bhyt
displayName: "Thẻ BHYT"
classify:
  anchors: ["THẺ BẢO HIỂM Y TẾ", "BẢO HIỂM XÃ HỘI VIỆT NAM"]

structuredData:
  - kind: qr
    parser: bhyt_qr          # giải mã QR -> mã số, họ tên, ngày sinh...
    mapsTo: [idNumber, fullName, dateOfBirth, sex]

extraction:
  strategy: label_anchored
  fields:
    - name: idNumber
      labels: ["Mã số", "Ma so"]
      take: after_colon
      source: [structured, ocr]
      type: code
      normalize: [removeSpaces, fixDigits]
      validate: { regex: '^\d{10}$' }     # mẫu mới; thêm '^[A-Z]{2}\d{13}$' nếu gặp thẻ cũ 15 ký tự
    - name: fullName
      labels: ["Họ và tên", "Họ tên"]
      take: after_colon
      source: [structured, ocr]
      type: text_vi
    - name: dateOfBirth
      labels: ["Ngày sinh", "Sinh ngày"]
      take: after_colon
      source: [structured, ocr]
      type: date
    - name: sex
      labels: ["Giới tính"]
      take: after_colon
      type: sex
    - name: benefitLevel
      labels: ["Giới tính"]            # số mức hưởng nằm cùng dòng giới tính
      take: trailing_digit
      type: digits
      validate: { regex: '^[1-5]$' }
    - name: registeredHospital
      labels: ["Nơi ĐK KCB BĐ", "Nơi đăng ký khám chữa bệnh ban đầu"]
      take: after_colon_or_below
      type: text_vi
      normalize: [dictFix]
    - name: validFrom
      labels: ["Giá trị sử dụng", "Giá trị sử dụng: từ ngày"]
      take: date_after_label
      type: date
    - name: fiveYearContinuous
      labels: ["Thời điểm đủ 05 năm liên tục", "đủ 05 năm liên tục"]
      take: date_after_label
      type: date
      required: false
    - name: issuePlace
      labels: ["Nơi cấp, đổi thẻ BHYT", "Nơi cấp đổi thẻ"]
      take: after_colon_or_below
      type: text_vi
    - name: dateOfIssue
      labels: ["Ngày", "tháng", "năm"]    # mẫu "Ngày .. tháng .. năm .."
      take: vn_date_phrase
      type: date
    - name: objectCode
      labels: ["Mã"]
      take: after_colon
      type: code
      required: false
```
