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
| Căn cước công dân | CCCD |
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

## 4. Danh mục loại giấy tờ chuẩn (10 loại V1)

CCCD/CMND đời cũ (trước 01/07/2024): chỉ xử lý **mặt trước** (xem DEC-008). Riêng
**Thẻ Căn cước 2024** nhận 1 ảnh mặt trước HOẶC mặt sau (mỗi mặt là một DOC-TYPE độc lập).

| Mã | Tên chuẩn (tiếng Việt) | Tên kỹ thuật | Dữ liệu máy đọc (mặt trước) | Ghi chú |
|---|---|---|---|---|
| DOC-TYPE-001 | CCCD gắn chip — Mặt trước | `cccd_chip_front` | **QR** (góc trên phải) | Số định danh 12 số; đã có mẫu, parser `cccd_qr` |
| DOC-TYPE-002 | CCCD mã vạch — Mặt trước | `cccd_barcode_front` | — | Bản cũ; barcode mặt sau (ngoài V1); đã có mẫu |
| DOC-TYPE-003 | CMND 09 số | `cmnd_9` | — | Giấy tờ cũ, 9 số; đã có mẫu |
| DOC-TYPE-004 | Hộ chiếu Việt Nam | `passport_vn` | **MRZ** | Trang nhân thân, MRZ 2 dòng (TD3); đã có mẫu cũ + mới |
| DOC-TYPE-005 | GPLX PET | `gplx_pet` | (QR tuỳ bản) | GPLX vật liệu PET; đã có mẫu (×3), có hạng Class |
| DOC-TYPE-006 | Thẻ BHYT | `bhyt` | **QR** (mẫu mới) | Mã số 10 số (mẫu mới) / 15 ký tự (cũ); đã có mẫu |
| DOC-TYPE-007 | Thẻ Đảng viên | `the_dang_vien` | — | Nội bộ; đã có mẫu, bóc tách label-anchored |
| DOC-TYPE-008 | Thẻ quân nhân | `the_quan_nhan` | — | Nội bộ, nhạy cảm, chờ ảnh mẫu |
| DOC-TYPE-009 | Căn cước 2024 — Mặt trước | `cccd_2024_front` | — | Thẻ "CĂN CƯỚC" từ 01/07/2024; mặt trước không QR |
| DOC-TYPE-010 | Căn cước 2024 — Mặt sau | `cccd_2024_back` | **QR + MRZ (TD1)** | Có địa chỉ, ngày cấp/hết hạn, chip |
| — | (Không xác định) | `unknown` | — | Trả khi không đủ tín hiệu phân loại |

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
