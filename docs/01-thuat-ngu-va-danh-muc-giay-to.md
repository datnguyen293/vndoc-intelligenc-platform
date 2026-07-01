# DOC-01 — Thuật ngữ & Danh mục giấy tờ

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-00

Tài liệu này là **nguồn chân lý** cho thuật ngữ, viết tắt và danh mục loại giấy tờ
của toàn dự án. Mọi tài liệu khác phải dùng đúng tên và mã ở đây.

## 1. Quy ước ngôn ngữ

- Tên nghiệp vụ và tên giấy tờ: **tiếng Việt** (có dấu).
- Tên kỹ thuật trong code và API: **tiếng Anh** (ví dụ field `idNumber`, `fullName`).
- Viết tắt chỉ dùng sau khi đã định nghĩa ở mục 2.

## 2. Viết tắt chuẩn

| Tên đầy đủ | Viết tắt |
|---|---|
| Căn cước công dân (thẻ "CĂN CƯỚC CÔNG DÂN", đến trước 01/07/2024) | CCCD |
| Căn cước (thẻ "CĂN CƯỚC" mẫu mới, từ 01/07/2024) | Căn cước |
| Chứng minh nhân dân | CMND |
| Giấy phép lái xe | GPLX |
| Bảo hiểm y tế | BHYT |
| Hộ chiếu | Hộ chiếu |
| Machine Readable Zone (vùng máy đọc chuẩn ICAO) | MRZ |
| Region of Interest (vùng quan tâm chứa 1 trường) | ROI |
| Optical Character Recognition | OCR |

## 3. Thuật ngữ kỹ thuật

| Thuật ngữ | Ý nghĩa |
|---|---|
| **Document type** | Loại giấy tờ chuẩn, có mã `DOC-TYPE-xxx` |
| **Plugin** | Gói mô tả cách xử lý một loại giấy tờ (manifest + ROI + validation + chuẩn hóa) |
| **Manifest** | File khai báo của plugin (YAML) |
| **ROI** | Vùng chữ nhật/đa giác chứa một trường dữ liệu trên ảnh đã nắn phẳng |
| **Template chuẩn** | Kích thước/khung quy chiếu của một mặt giấy tờ sau khi nắn phẳng |
| **Rectification** | Nắn phối cảnh ảnh giấy tờ về template chuẩn |
| **Structured-data zone** | Vùng dữ liệu máy đọc: QR, MRZ, barcode |
| **Field** | Một trường dữ liệu đầu ra (ví dụ số định danh, họ tên) |
| **Confidence** | Độ tin cậy [0..1] của một trường hoặc của cả kết quả |

## 4. Danh mục loại giấy tờ chuẩn (V1)

CCCD/CMND đời cũ (trước 01/07/2024): chỉ xử lý **mặt trước** (xem DEC-008). Riêng
**Thẻ Căn cước 2024** nhận 1 ảnh mặt trước HOẶC mặt sau (mỗi mặt là một DOC-TYPE độc lập).

**Hint thô theo HỌ (DEC-044):** client KHÔNG phân biệt loại con (cán bộ chỉ biết "CMND"
hay "CCCD"). Vì vậy `docTypeHint` chỉ gửi **họ** `cmnd` hoặc `cccd`; hệ thống TỰ nhận
loại con. Họ `cmnd` = {CMND 9 số, CMND 12 số}; họ `cccd` = {CCCD gắn chip mặt trước,
Căn cước 2024 mặt trước, Căn cước 2024 mặt sau}. Quy tắc nhận loại con xem DOC-05.

| Mã | Tên chuẩn (tiếng Việt) | Tên kỹ thuật | Họ | Dữ liệu máy đọc | Ghi chú |
|---|---|---|---|---|---|
| DOC-TYPE-001 | CCCD gắn chip — Mặt trước | `cccd_chip_front` | `cccd` | **QR** (góc trên phải, nhỏ) | Title "CĂN CƯỚC CÔNG DÂN" (trước 01/07/2024); parser `cccd_qr` |
| DOC-TYPE-002 | CMND 12 số (thẻ cứng) | `cmnd_12` | `cmnd` | — | Title "CHỨNG MINH NHÂN DÂN", số 12 chữ số (đổi tên từ `cccd_barcode_front`) |
| DOC-TYPE-003 | CMND 9 số (giấy cũ) | `cmnd_9` | `cmnd` | — | Title "GIẤY CHỨNG MINH NHÂN DÂN", số 9 chữ số; rất cũ, còn ít người dùng |
| DOC-TYPE-004 | Hộ chiếu Việt Nam | `passport_vn` | — | **MRZ (TD3)** | Trang nhân thân; 1 docType phủ CẢ 2 layout cũ (Họ và tên, số GCMND 9 số) + mới (Họ/Surname tách, số ĐDCN 12 số) |
| DOC-TYPE-005 | GPLX PET | `gplx_pet` | — | (QR tuỳ bản) | GPLX vật liệu PET; có hạng Class |
| DOC-TYPE-006 | Thẻ BHYT | `bhyt` | — | **QR** (mẫu mới) | Mã số 10 số; QR đọc được → dừng OCR (structuredComplete) |
| DOC-TYPE-007 | Thẻ Đảng viên | `the_dang_vien` | — | — | Nội bộ; label-anchored |
| DOC-TYPE-008 | Thẻ quân nhân | `the_quan_nhan` | — | — | "CHỨNG MINH QUÂN NHÂN CHUYÊN NGHIỆP"; Số 12 số + họ tên + sinh + đơn vị; OCR thuần (không QR) |
| DOC-TYPE-009 | Căn cước 2024 — Mặt trước | `cccd_2024_front` | `cccd` | — | Title "CĂN CƯỚC" (KHÔNG "CÔNG DÂN"), song ngữ; QR ở mặt sau → mặt trước OCR thuần |
| DOC-TYPE-010 | Căn cước 2024 — Mặt sau | `cccd_2024_back` | `cccd` | **QR + MRZ (TD1)** | "Nơi cư trú", "BỘ CÔNG AN"; QR cho định danh, OCR bù |
| — | (Không xác định) | `unknown` | — | — | Trả khi không đủ tín hiệu phân loại |

> **Đổi tên (2026-06):** `cccd_barcode_front` → `cmnd_12`. Thẻ "12 số" trước đây gọi
> nhầm là "CCCD mã vạch" thực chất là **CMND 12 số** (title "CHỨNG MINH NHÂN DÂN"). Bỏ
> khái niệm "CCCD mã vạch" khỏi danh mục.

## 5. Quy tắc mã định danh

| Loại | Định dạng | Ví dụ |
|---|---|---|
| Requirement | `FR-xxx` | FR-007 |
| Non-functional | `NFR-xxx` | NFR-001 |
| Decision | `DEC-xxx` | DEC-005 |
| Architecture Decision Record | `ADR-xxx` | ADR-002 |
| API endpoint | `API-xxx` | API-001 |
| Plugin | `PLG-xxx` | PLG-001 |
| Loại giấy tờ | `DOC-TYPE-xxx` | DOC-TYPE-002 |
| Test case | `TST-xxx` | TST-014 |

## 6. Tên trường dữ liệu chuẩn (preview)

Bộ tên trường đầy đủ và quy tắc chuẩn hóa đặt tại DOC-08. Một số tên dùng chung:

| Tên kỹ thuật | Nghĩa | Áp dụng |
|---|---|---|
| `idNumber` | Số định danh / số giấy tờ | CCCD, CMND, hộ chiếu... |
| `fullName` | Họ và tên | Hầu hết |
| `dateOfBirth` | Ngày sinh (ISO `YYYY-MM-DD`) | Hầu hết |
| `sex` | Giới tính (`Nam`/`Nữ`) | Hầu hết |
| `nationality` | Quốc tịch | CCCD, hộ chiếu |
| `placeOfOrigin` | Quê quán | CCCD, CMND |
| `placeOfResidence` | Nơi thường trú | CCCD, CMND |
| `dateOfIssue` | Ngày cấp | Hầu hết |
| `dateOfExpiry` | Ngày hết hạn | CCCD, hộ chiếu, GPLX |
| `issuedBy` | Nơi cấp | Hầu hết |

## 7. Nguyên tắc nhất quán

- Mỗi loại giấy tờ chỉ có **một** tên chuẩn và **một** mã `DOC-TYPE`.
- Viết tắt phải giống nhau trong mọi tài liệu.
- Code dùng tên kỹ thuật tiếng Anh; tài liệu nghiệp vụ dùng tên chuẩn tiếng Việt.
