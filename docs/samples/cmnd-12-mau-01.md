# Mẫu tham chiếu — CMND 12 số (thẻ cứng) #01

- **Loại:** `cmnd_12` (DOC-TYPE-002) — *đổi tên từ `cccd_barcode_front`*.
- **Mục đích:** ảnh mẫu thật để hiệu chỉnh nhãn/regex (KHÔNG để train).
- **Nguồn:** `samples/cmnd_12/thuy-giang.jpeg` — 2026-06.
- **Lưu ý taxonomy:** thẻ ghi **"CHỨNG MINH NHÂN DÂN"**, số **12 chữ số** → đây là
  **CMND 12 số** (thẻ cứng), KHÔNG phải "CCCD mã vạch". Khái niệm "CCCD mã vạch" đã bỏ
  khỏi danh mục (xem DOC-01 §4). Phân biệt với CMND 9 số bằng **độ dài số** (DEC-045).

## 1. Nhãn & giá trị (ground truth)

| Nhãn | Trường | Giá trị |
|---|---|---|
| `Số` | `idNumber` | 001192004768 (12 số) |
| `Họ và tên khai sinh` | `fullName` | NGUYỄN THÙY GIANG |
| `Ngày, tháng, năm sinh` | `dateOfBirth` | 24/09/1992 → 1992-09-24 |
| `Giới tính` | `sex` | Nữ |
| `Dân tộc` | (—) | Kinh (không bóc tách V1) |
| `Quê quán` | `placeOfOrigin` | Tân Triều, Thanh Trì, Hà Nội |
| `Nơi thường trú` | `placeOfResidence` | P29-B12 TT Kim Liên, Kim Liên, Đống Đa, Hà Nội |
| `Có giá trị đến` | `dateOfExpiry` | 04/11/2030 → 2030-11-04 |

- **Không có QR/mã máy đọc ở mặt thông tin** → bóc tách thuần OCR (`label_anchored`).
- `Quê quán`, `Nơi thường trú` xuống 2 dòng → gộp dòng (`multiline`).

## 2. Phát hiện ảnh hưởng thiết kế

1. **Phân biệt CMND 9 vs 12 = độ dài số** (DEC-045): có dãy ≥12 số → `cmnd_12`; ngược
   lại → `cmnd_9`. Bền cả khi OCR đọc sai vài chữ số 9 (chỉ cần VẮNG dãy 12).
2. Cùng cụm tiêu đề "CHỨNG MINH NHÂN DÂN" với CMND 9 (loại 9 có thêm "GIẤY") → anchor
   chung, không tự tách bằng title được.
3. 3 số đầu `idNumber` = mã tỉnh → cross-check với quê quán/thường trú (`crossCheckProvince`).
4. Title đỏ + số đỏ in chìm → OCR có thể nhiễu; QR vắng nên idNumber chỉ từ OCR.

## 3. Plugin: xem `service/plugins/cmnd_12/manifest.yaml`. Golden: `cmnd_12__thuy-giang`.
