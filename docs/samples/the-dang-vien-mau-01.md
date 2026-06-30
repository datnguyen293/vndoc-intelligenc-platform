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
