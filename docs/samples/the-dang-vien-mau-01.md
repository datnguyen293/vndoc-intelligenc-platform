# Mẫu tham chiếu — Thẻ Đảng viên #01

- **Loại:** `the_dang_vien` (DOC-TYPE-007)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** nhãn/regex (KHÔNG dùng để train).
- **Nguồn:** 1 ảnh thẻ Đảng viên do người dùng cung cấp (2026-06-29).

## 1. Quan sát căn chỉnh

- Ảnh **đúng chiều** (không xoay), thẻ dạng dọc (portrait), nền hoa văn búa liềm mờ.
- Bố cục: tiêu đề đỏ trên cùng → số thẻ → cột nhãn–giá trị → ngày cấp → ảnh chân
  dung góc dưới trái → dấu tròn đỏ "ĐẢNG CỘNG SẢN VIỆT NAM - BAN CHẤP HÀNH TRUNG ƯƠNG".
- Nhãn rõ ràng, in đậm → **`label_anchored` là chiến lược chính** (không cần ROI cố định).

## 2. Nhãn in trên thẻ (verbatim)

| Nhãn | Trường | Ghi chú |
|---|---|---|
| `Số` (dưới tiêu đề) | `cardNumber` | định dạng `NN.NNNNNN` |
| `Họ và tên` | `fullName` | không có dấu `:` — giá trị bên phải nhãn |
| `Sinh ngày` | `dateOfBirth` | dd - MM - yyyy |
| `Quê quán` | `placeOfOrigin` | có thể xuống dòng |
| `Vào Đảng ngày` | `partyJoinDate` | dd - MM - yyyy |
| `Chính thức ngày` | `officialDate` | dd - MM - yyyy |
| `Nơi cấp thẻ` | `partyOrganization` | tên đảng bộ, có thể xuống dòng |
| `Ngày … tháng … năm` | `dateOfIssue` | ngày cấp thẻ |

Lưu ý: nhãn ở thẻ này **không có dấu `:`** → dùng `take: right_of_label` /
`take: below_label`, không phải `after_colon`.

## 2b. MẪU MỚI (ngoc-hung, 2026-07-01) — cùng docType, khác template

Thẻ Đảng viên có **2 mẫu** (gộp trong 1 plugin, như BHYT/hộ chiếu). Mẫu mới khác:

| Điểm | Mẫu cũ (thuy-giang) | Mẫu mới (ngoc-hung) |
|---|---|---|
| Số thẻ | `NN.NNNNNN` | **12 chữ số** (`001088023765`) → regex nới `(\d{2}\.\d{6}\|\d{12})` |
| Họ tên | nhãn `HỌ VÀ TÊN` | **KHÔNG nhãn** (dòng chữ hoa trên các ngày) → take `vi_name_orphan` |
| Ngày sinh | `Sinh ngày` | `Ngày sinh` (giá trị **xuống dòng**) |
| Vào Đảng | `Vào Đảng ngày` | `Ngày vào Đảng` |
| Nơi cấp | `Nơi cấp thẻ` | `Nơi cấp` (xuống 2 dòng "Đảng Bộ / Công An Trung Ương") |
| Ngày cấp | câu `Ngày..tháng..năm` | `Ngày cấp: dd-mm-yyyy` → take `date_phrase_or_issue` |
| Quê quán / Chính thức | có | **KHÔNG có** (→ null) |

## 2c. QR-first cho mẫu mới (ADR-006) — ưu tiên QR, đọc được thì DỪNG OCR

Mẫu mới có **QR bề mặt ĐỦ 7 trường** (`structuredComplete: true`), **đầy đủ hơn OCR** — có
`officialDate` và `partyOrganization` KHÔNG bị cụt. Định dạng payload (ngăn `|`):

```
[0] số thẻ 12 số   [1] họ tên (có dấu)   [2] ngày sinh ddMMyyyy   [3] ngày vào Đảng ddMMyyyy
[4] ngày chính thức ddMMyyyy   [5] nơi cấp/đảng bộ   [6] ngày cấp ddMMyyyy
```
Ví dụ: `001088023765|NGUYỄN NGỌC HƯNG|13021988|14062011|14062012|Đảng Bộ Công An Trung Ương|14092025`

- Parser `dang_vien_qr` **siết cấu trúc** (các trường ngày [2][3][6] phải `ddMMyyyy`) để
  KHÔNG nhận nhầm QR CCCD ([2]=họ tên) / BHYT ([3]=giới tính) — 2 loại này cũng ngăn `|`.
- QR **nhỏ trong ảnh lớn** (thẻ 1600px, QR ~90px): `identify()` phóng to ảnh khi
  `hint=the_dang_vien` để đọc QR ở fast-path RỒI BỎ QUA OCR (đọc QR xong không OCR).
- Mẫu CŨ không có QR → `dang_vien_qr` trả `{}` → rơi về OCR label-anchored (mục 2b).

## 2d. Phân loại — HINT là chính, anchor là phụ

- **Cơ chế chính:** client gửi `docTypeHint=the_dang_vien` → classifier **tin hint** (0.95),
  không phụ thuộc anchor → không có va chạm. (Officer biết đây là thẻ Đảng viên.)
- **Phòng thủ (khi KHÔNG hint):** chấm điểm anchor. Tiêu đề OCR méo `THẾ ĐẶNG VIỆN` vẫn khớp
  `THẺ ĐẢNG VIÊN` sau `key()` (bỏ dấu). Mẫu mới ghi "Đảng **Bộ Công An** Trung Ương" trùng
  anchor `BỘ CÔNG AN` của `cccd_2024_back` → thêm anti-anchor `excludes: [THẺ ĐẢNG VIÊN]`
  cho `cccd_2024_back` để không nhận nhầm ở đường không-hint.
- Hạn chế OCR-fallback đã biết: `partyOrganization` mẫu mới qua OCR bị **cụt** còn "Đằng Bộ"
  (mất dòng 2) do `_MERGE_CAP=1` toàn cục — nhưng **đường QR-first cho org ĐẦY ĐỦ**, nên chỉ
  ảnh hưởng khi QR hỏng. Không đổi hằng số chung (tránh hồi quy địa chỉ các loại khác).

## 3. Giá trị mẫu (ground truth)

| Trường | Giá trị | Chuẩn hóa |
|---|---|---|
| cardNumber | 83.060977 | 83.060977 |
| fullName | NGUYỄN THÙY GIANG | NGUYỄN THÙY GIANG |
| dateOfBirth | 24 - 09 - 1992 | 1992-09-24 |
| placeOfOrigin | X. Tân Triều, H. Thanh Trì, TP. Hà Nội | (giữ nguyên) |
| partyJoinDate | 19 - 05 - 2023 | 2023-05-19 |
| officialDate | 19 - 05 - 2024 | 2024-05-19 |
| partyOrganization | Đảng bộ Khối các cơ quan Trung ương | (gộp 2 dòng) |
| dateOfIssue | Ngày 07 tháng 11 năm 2024 | 2024-11-07 |

> Dữ liệu cá nhân thật — chỉ dùng nội bộ để hiệu chỉnh, không phát tán (NFR-007).

## 4. Phát hiện ảnh hưởng thiết kế

1. **Trường `placeOfOrigin` (Quê quán)** — đã bổ sung vào DOC-08 §3 (DOC-TYPE-007).
2. **Số thẻ định dạng `NN.NNNNNN`** (có dấu chấm), vd `83.060977` → regex `^\d{2}\.\d{6}$`
   (nới lỏng nếu gặp mẫu khác).
3. Nhãn **không có dấu `:`** → cần `take: right_of_label` và `below_label`.
4. Ngày dạng `dd - MM - yyyy` (có khoảng trắng quanh `-`) → bộ parse ngày phải chịu
   được dấu cách và `-`.
5. `partyOrganization` và `placeOfOrigin` **xuống 2 dòng** → cần gộp dòng kế tiếp.
6. Thẻ **không có** giới tính, không có hạn dùng.
7. Plugin chuyển từ trạng thái "chờ mẫu" → **`ready: true`** (label-anchored, không
   cần ROI cố định). Vẫn nên thu thêm vài mẫu để kiểm độ ổn định nhãn.

## 5. Draft plugin Thẻ Đảng viên (bám nhãn)

```yaml
docType: the_dang_vien
displayName: "Thẻ Đảng viên"
ready: true
classify:
  anchors: ["THẺ ĐẢNG VIÊN", "ĐẢNG CỘNG SẢN VIỆT NAM"]

extraction:
  strategy: label_anchored
  fields:
    - name: cardNumber
      labels: ["Số"]
      take: right_of_label
      type: code
      normalize: [trim]
      validate: { regex: '^\d{2}\.\d{6}$' }
    - name: fullName
      labels: ["Họ và tên", "Họ tên"]
      take: right_of_label
      type: text_vi
    - name: dateOfBirth
      labels: ["Sinh ngày"]
      take: date_after_label
      type: date
    - name: placeOfOrigin
      labels: ["Quê quán"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces, dictFix]
    - name: partyJoinDate
      labels: ["Vào Đảng ngày"]
      take: date_after_label
      type: date
    - name: officialDate
      labels: ["Chính thức ngày"]
      take: date_after_label
      type: date
    - name: partyOrganization
      labels: ["Nơi cấp thẻ"]
      take: right_of_label_or_below
      type: text_vi
      normalize: [collapseSpaces]
    - name: dateOfIssue
      labels: ["Ngày", "tháng", "năm"]
      take: vn_date_phrase
      type: date
      required: false
```
