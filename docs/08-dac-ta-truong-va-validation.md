# DOC-08 — Đặc tả trường & Validation

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-01, DOC-05
- **Truy vết:** FR-010, FR-011, FR-012, FR-013

Tài liệu này khai báo **tập trường** của từng loại giấy tờ, quy tắc **validate**,
**chuẩn hóa** và **đối chiếu chéo**. Là đầu vào trực tiếp để viết manifest plugin.

> Ghi chú: ROI (toạ độ) **không** nằm ở đây — chúng thuộc manifest plugin (DOC-05).
> Tài liệu này định nghĩa *ý nghĩa, kiểu, quy tắc* của trường, độc lập với toạ độ.

---

## 1. Từ điển trường chuẩn (data dictionary)

| Tên kỹ thuật | Nhãn tiếng Việt | Kiểu | Chuẩn hóa | Validate |
|---|---|---|---|---|
| `idNumber` | Số (định danh/giấy tờ) | digits/code | bỏ space, sửa O→0 I→1 | theo loại (xem §3) |
| `fullName` | Họ và tên | text_vi | gộp space, viết HOA có dấu | `^[\p{L}\s]{2,}$` |
| `dateOfBirth` | Ngày sinh | date | → ISO `YYYY-MM-DD` | hợp lệ, không tương lai |
| `sex` | Giới tính | sex | → `Nam`/`Nữ` | ∈ {Nam, Nữ} |
| `nationality` | Quốc tịch | text_vi | chuẩn "Việt Nam" | dictionary quốc gia |
| `placeOfOrigin` | Quê quán / Nguyên quán | text_vi | gộp space, sửa theo địa danh | dictionary tỉnh/thành |
| `placeOfResidence` | Nơi thường trú / cư trú | text_vi | gộp space, sửa địa danh | không rỗng |
| `placeOfBirth` | Nơi sinh | text_vi | gộp space | dictionary tỉnh/thành |
| `dateOfIssue` | Ngày cấp | date | → ISO | hợp lệ, ≤ hôm nay |
| `dateOfExpiry` | Có giá trị đến / hết hạn | date | → ISO hoặc `Không thời hạn` | hợp lệ |
| `issuedBy` | Nơi cấp / cơ quan cấp | text_vi | gộp space | không rỗng |

Các trường đặc thù khác khai báo tại §3.

---

## 2. Quy tắc chuẩn hóa (normalization)

| Hàm | Mô tả |
|---|---|
| `trim` | bỏ khoảng trắng đầu/cuối |
| `collapseSpaces` | gộp nhiều khoảng trắng thành một |
| `removeSpaces` | bỏ hết khoảng trắng (cho số) |
| `stripDots` | bỏ ký tự chấm/đường gạch chấm thừa do OCR đường kẻ (CMND cũ) |
| `dotSeparator` | mã dạng `số.số`: ép dấu phân cách OCR đọc nhầm (`:`,`,`,space) về `.` |
| `upperVi` | viết HOA giữ dấu tiếng Việt (Unicode) |
| `toIsoDate` | `dd/MM/yyyy` (và biến thể) → `yyyy-MM-dd` |
| `fixDigits` | sửa nhầm OCR: O→0, I/l→1, B→8, S→5 trong ngữ cảnh số |
| `dictFix` | khớp gần đúng với dictionary (Levenshtein) cho địa danh/dân tộc |
| `normSex` | "NAM/M/Male"→`Nam`, "NỮ/F/Female"→`Nữ` |

Quy tắc ngày tháng:
- Chấp nhận `dd/MM/yyyy`, `dd-MM-yyyy`, `dd.MM.yyyy`.
- CMND 9 số đôi khi chỉ có **năm sinh** → cho phép `yyyy` (lưu `1990-00-00`? → KHÔNG;
  giữ `value` rỗng phần ngày, đặt cờ `partialDate: true`, `raw` giữ nguyên).

---

## 3. Tập trường theo từng loại giấy tờ

### DOC-TYPE-001 — CCCD gắn chip (Mặt trước)
Đã hiệu chỉnh theo mẫu thật ([samples/cccd-chip-mau-01.md](samples/cccd-chip-mau-01.md)).
Nguồn ưu tiên: **QR ở góc trên phải mặt trước** → OCR bù/đối chiếu.

| Trường | Bắt buộc | Nguồn | Validate riêng |
|---|---|---|---|
| `idNumber` | có | structured, ocr | `^\d{12}$`; 3 số đầu = mã tỉnh |
| `fullName` | có | structured, ocr | `^[\p{L}\s]{2,}$` |
| `dateOfBirth` | có | structured, ocr | ngày hợp lệ |
| `sex` | có | structured, ocr | Nam/Nữ |
| `nationality` | có | **ocr** | mặc định "Việt Nam" (QR không có) |
| `placeOfOrigin` | có | **ocr** | dictionary tỉnh/thành (QR không có) |
| `placeOfResidence` | có | structured, ocr | không rỗng |
| `dateOfExpiry` | có | **ocr** | ngày hợp lệ (QR không có); cảnh báo `da_het_han` |
| `dateOfIssue` | không | **structured** | chỉ từ QR (không in trên mặt trước) |
| `oldIdNumber` (số CMND 9 số cũ) | không | **structured** | `^\d{9}$`; chỉ từ QR |

QR `mapsTo`: `idNumber, oldIdNumber, fullName, dateOfBirth, sex, placeOfResidence, dateOfIssue`.
Lưu ý: QR **không chứa** `nationality`, `placeOfOrigin`, `dateOfExpiry` → 3 trường này
chỉ lấy bằng OCR. QR **có** `dateOfIssue` (không in trên mặt) và `oldIdNumber`.
Cross-check: 3 số đầu `idNumber` = mã tỉnh ↔ tỉnh trong quê quán/nơi thường trú.

### DOC-TYPE-002 — CCCD mã vạch (Mặt trước)
Đã hiệu chỉnh theo mẫu thật ([samples/cccd-ma-vach-mau-01.md](samples/cccd-ma-vach-mau-01.md)).
Thuần OCR (barcode ở mặt sau, ngoài phạm vi); `source: [ocr]` cho mọi trường.

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` | có | ocr | `^\d{12}$`; 3 số đầu = mã tỉnh |
| `fullName` | có | ocr | text_vi |
| `dateOfBirth` | có | ocr | nhãn "Ngày, tháng, năm sinh"; dd/MM/yyyy |
| `sex` | có | ocr | nhãn "Giới tính" (cùng hàng "Quốc tịch") |
| `nationality` | có | ocr | mặc định "Việt Nam" |
| `placeOfOrigin` | có | ocr | nhãn "Quê quán"; có thể xuống dòng |
| `placeOfResidence` | có | ocr | nhãn "Nơi thường trú"; có thể xuống dòng |
| `dateOfExpiry` | có | ocr | nhãn "Có giá trị đến"; cảnh báo `da_het_han` |

Cross-check: 3 số đầu `idNumber` = mã tỉnh → đối chiếu với tỉnh trong quê quán/nơi
thường trú (cảnh báo nếu lệch). Phân biệt với CCCD gắn chip bằng **không có QR mặt trước**.

### DOC-TYPE-003 — CMND 09 số
Đã hiệu chỉnh theo mẫu thật ([samples/cmnd-9-mau-01.md](samples/cmnd-9-mau-01.md)).

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` | có | ocr | `^\d{9}$` (số in đỏ, đè dấu → OCR khó, không checksum) |
| `fullName` | có | ocr | nhãn "Họ tên" |
| `dateOfBirth` | có | ocr | nhãn "Sinh ngày"; cho phép chỉ năm (`partialDate`) |
| `placeOfOrigin` | có | ocr | nhãn "Nguyên quán"; có thể xuống dòng |
| `placeOfResidence` | có | ocr | nhãn "Nơi ĐKHK thường trú"; có thể xuống dòng |

Lưu ý:
- Mặt trước CMND 9 số **không có** giới tính/quốc tịch/hạn dùng → chỉ 5 trường trên.
- **Số in màu đỏ đè dấu giáp lai** → tăng tương phản kênh đỏ ở ROI số; confidence
  thấp hơn; ràng buộc `^\d{9}$`; cho phép sửa tay.
- Giá trị nằm trên **đường gạch chấm** → hậu xử lý `stripDots` bỏ ký tự chấm thừa.

### DOC-TYPE-004 — Hộ chiếu Việt Nam
Đã hiệu chỉnh theo **2 mẫu thật**: [cũ #01](samples/ho-chieu-mau-01.md) và
[mới/e-passport #02](samples/ho-chieu-mau-02.md). Cùng `docType` `passport_vn`,
plugin **tự nhận layout cũ/mới**. Nguồn ưu tiên: **MRZ (TD3, có checksum)** → OCR
vùng nhìn bù/đối chiếu. Nhãn **song ngữ Việt/Anh**, nhãn-trên-giá-trị → `take: below_label`.

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` (số hộ chiếu) | có | structured(mrz), ocr | `^[A-Z]\d{7,8}$` (cũ B7849474 / mới E01828939) |
| `surname` (Họ) | mẫu mới | ocr, structured | text_vi (chỉ mẫu mới tách riêng) |
| `givenNames` (Chữ đệm và tên) | mẫu mới | ocr, structured | text_vi (chỉ mẫu mới) |
| `fullName` | có | **ocr** (giữ dấu), structured | mẫu cũ: lấy "Họ và tên"; mẫu mới: `surname`+" "+`givenNames`; cross-check MRZ (bỏ dấu) |
| `nationality` | có | structured, ocr | "Việt Nam"/VNM |
| `dateOfBirth` | có | structured, ocr | ngày hợp lệ |
| `sex` | có | structured, ocr | Nam/Nữ |
| `placeOfBirth` | không | ocr | dictionary tỉnh/thành |
| `personalIdNumber` | không | structured(mrz), ocr | `^\d{9}$\|^\d{12}$` (GCMND 9 số / ĐDCN 12 số) |
| `dateOfIssue` | có | ocr | ngày hợp lệ |
| `dateOfExpiry` | có | structured, ocr | ngày hợp lệ; cảnh báo `da_het_han` nếu < hôm nay |
| `issuedBy` | không | ocr | "Cục Quản lý xuất nhập cảnh"; mẫu mới có thể trống |
| `passportType` (Loại) | không | ocr | vd "P" |
| `countryCode` (Mã số) | không | structured, ocr | vd "VNM" |

MRZ `mapsTo`: `idNumber, nationality, surname, givenNames, dateOfBirth, sex, dateOfExpiry, personalIdNumber` (+ check digits).
Lưu ý: **tên trong MRZ không dấu** → `surname`/`givenNames`/`fullName` ưu tiên OCR
vùng nhìn. Nhãn định danh có **3 dạng**: "Số GCMND / ID card No" (cũ, 9 số), "Số
định danh cá nhân / Personal No" và "Số ĐDCN, CMND / ID No." (mới, 12 số).

### DOC-TYPE-005 — GPLX PET
Đã hiệu chỉnh theo 3 mẫu thật ([samples/gplx-pet-mau-01.md](samples/gplx-pet-mau-01.md)).
Nhãn **song ngữ Việt/Anh**; thường **không có QR** (để ngỏ cho bản mới).

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` (số GPLX) | có | structured(qr nếu có), ocr | `^\d{12}$` (2 số đầu = mã tỉnh cấp) |
| `fullName` | có | ocr | text_vi |
| `dateOfBirth` | có | ocr | ngày hợp lệ |
| `nationality` | không | ocr | "Việt Nam" |
| `placeOfResidence` (nơi cư trú) | có | ocr | không rỗng; có thể xuống dòng |
| `licenseClass` (hạng) | có | ocr | ∈ {A1,A2,A3,A4,B1,B2,C,D,E,FB2,FC,FD,FE} |
| `dateOfIssue` | không | ocr | từ câu "[Nơi], ngày DD tháng MM năm YYYY" (`vn_date_phrase`) |
| `issuePlace` (nơi cấp) | không | ocr | tỉnh/thành đứng trước "ngày" trong câu cấp |
| `dateOfExpiry` | có | ocr | ngày; cảnh báo `da_het_han` |

Lưu ý: **dấu mộc + chữ ký đè** vùng ngày cấp/nơi cấp → các trường này confidence thấp
hơn; ưu tiên `dateOfExpiry` (rõ) làm trường chắc. Hạng (Class) là trường nghiệp vụ
quan trọng — validate theo enum.

### DOC-TYPE-006 — Thẻ BHYT
Đã hiệu chỉnh theo mẫu thật (xem [samples/bhyt-mau-01.md](samples/bhyt-mau-01.md)).
Mẫu mới (2021+) có **QR** trên mặt thông tin → structured-data-first dùng được.

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` (mã số BHYT) | có | structured(qr), ocr | `^\d{10}$` (mẫu mới); thẻ cũ `^[A-Z]{2}\d{13}$` |
| `fullName` | có | structured(qr), ocr | text_vi |
| `dateOfBirth` | có | structured(qr), ocr | cho phép chỉ năm |
| `sex` | có | structured(qr), ocr | Nam/Nữ |
| `benefitLevel` (mức hưởng) | không | ocr | `^[1-5]$` |
| `registeredHospital` (nơi ĐK KCB BĐ) | có | ocr | dictionary CSYT |
| `validFrom` (giá trị sử dụng từ ngày) | có | ocr | ngày hợp lệ |
| `fiveYearContinuous` (đủ 5 năm liên tục từ) | không | ocr | ngày hợp lệ |
| `issuePlace` (nơi cấp, đổi thẻ) | không | ocr | không rỗng |
| `dateOfIssue` (ngày cấp thẻ) | không | ocr | ngày hợp lệ |
| `objectCode` (mã đối tượng, vd 01-C54) | không | ocr | — |

Ghi chú:
- **Mã số mẫu mới = 10 chữ số** (không còn 15 ký tự như mẫu cũ). Plugin chấp nhận cả
  hai dạng để tương thích thẻ cũ.
- Mẫu mới **bỏ trường "Địa chỉ"**; thay bằng `issuePlace` + `registeredHospital`.
- Nhãn dùng **viết tắt** ("Nơi ĐK KCB BĐ") → manifest khớp cả viết tắt lẫn đầy đủ.

### DOC-TYPE-007 — Thẻ Đảng viên  *(nội bộ — đã hiệu chỉnh theo mẫu thật)*
Xem [samples/the-dang-vien-mau-01.md](samples/the-dang-vien-mau-01.md). Bóc tách bằng
`label_anchored` (không cần ROI cố định) → plugin `ready: true`.

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `cardNumber` (số thẻ đảng viên) | có | ocr | `^\d{2}\.\d{6}$` (vd 83.060977) |
| `fullName` | có | ocr | text_vi |
| `dateOfBirth` (sinh ngày) | có | ocr | ngày hợp lệ |
| `placeOfOrigin` (quê quán) | có | ocr | text_vi, dictionary tỉnh/thành |
| `partyJoinDate` (vào Đảng ngày) | có | ocr | ngày hợp lệ |
| `officialDate` (chính thức ngày) | không | ocr | ngày hợp lệ |
| `partyOrganization` (nơi cấp thẻ/đảng bộ) | không | ocr | text_vi |
| `dateOfIssue` (ngày cấp thẻ) | không | ocr | ngày hợp lệ |

Ghi chú: nhãn trên thẻ **không có dấu `:`** (giá trị nằm bên phải/dưới nhãn); ngày
dạng `dd - MM - yyyy`; `quê quán`/`nơi cấp thẻ` có thể xuống dòng → cần gộp dòng.

### DOC-TYPE-008 — Thẻ quân nhân  *(nội bộ, nhạy cảm — ROI chờ ảnh mẫu)*
| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `cardNumber` / `serviceNumber` (số hiệu) | có | ocr | theo mẫu thật |
| `fullName` | có | ocr | text_vi |
| `dateOfBirth` | có | ocr | ngày hợp lệ |
| `rank` (cấp bậc) | không | ocr | dictionary cấp bậc QĐND |
| `unit` (đơn vị) | không | ocr | text_vi |
| `dateOfIssue` | không | ocr | ngày hợp lệ |
| `dateOfExpiry` | không | ocr | ngày hợp lệ |

> Lưu ý bảo mật (NFR-007): dữ liệu thẻ quân nhân nhạy cảm — không log toàn văn, mask
> `cardNumber`/`serviceNumber` trong log; cân nhắc cấu hình tắt lưu ảnh hoàn toàn.

### DOC-TYPE-009 — Căn cước 2024 — Mặt trước
Thẻ "CĂN CƯỚC" từ 01/07/2024 (xem [samples/cccd-2024-mau-01.md](samples/cccd-2024-mau-01.md)).
Mặt trước **rút gọn, không có QR**; nhãn song ngữ Việt/Anh.

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` (số định danh cá nhân) | có | ocr | `^\d{12}$`; 3 số đầu = mã tỉnh |
| `fullName` (họ, chữ đệm và tên khai sinh) | có | ocr | text_vi |
| `dateOfBirth` | có | ocr | ngày hợp lệ |
| `sex` | có | ocr | Nam/Nữ |
| `nationality` | có | ocr | mặc định "Việt Nam" |

Lưu ý: mặt trước **không có** địa chỉ, quê quán, ngày cấp, hạn dùng (đều ở mặt sau).
Phân loại: tiêu đề **"CĂN CƯỚC"** (không có "CÔNG DÂN"), không QR mặt trước.

### DOC-TYPE-010 — Căn cước 2024 — Mặt sau
Nguồn ưu tiên: **MRZ TD1 (3 dòng, có checksum) + QR** → OCR bù/đối chiếu.

| Trường | Bắt buộc | Nguồn | Validate |
|---|---|---|---|
| `idNumber` (số định danh) | có | structured(mrz/qr), ocr | `^\d{12}$` |
| `fullName` | có | structured, ocr | text_vi (MRZ/OCR; OCR giữ dấu) |
| `dateOfBirth` | có | structured, ocr | ngày hợp lệ |
| `sex` | có | structured, ocr | Nam/Nữ |
| `placeOfResidence` (nơi cư trú) | có | structured(qr), ocr | không rỗng; có thể xuống dòng |
| `placeOfBirth` (nơi đăng ký khai sinh) | không | ocr | dictionary tỉnh/thành |
| `dateOfIssue` (ngày cấp) | có | ocr | ngày hợp lệ |
| `dateOfExpiry` (ngày hết hạn) | có | structured, ocr | ngày hợp lệ; cảnh báo `da_het_han` |
| `issuedBy` | không | ocr | "Bộ Công an" |

MRZ TD1 `mapsTo`: `idNumber, fullName, dateOfBirth, sex, dateOfExpiry`. Cần parser
`mrz_td1` (khác `mrz_td3` của hộ chiếu). QR mặt sau cần xác định lại định dạng (có thể
khác QR mặt trước của CCCD gắn chip) → parser `cccd_qr` cấu hình theo biến thể.

---

## 4. Đối chiếu chéo (cross-check)

Khi một trường có cả nguồn `structured` và `ocr`:
1. Chuẩn hóa cả hai về cùng dạng.
2. So khớp:
   - **Khớp** → `value` lấy nguồn structured, `confidence` nâng lên (vd min(0.99, +0.1)).
   - **Lệch** → `value` ưu tiên `structured` (QR/MRZ chính xác hơn), thêm
     `warnings: ["{field}_lech_giua_qr_va_ocr"]`, hạ confidence.
3. Với MRZ: dùng **check digit** để xác nhận; nếu checksum sai → coi MRZ kém tin cậy,
   ưu tiên OCR và cảnh báo.

Đối chiếu logic nội tại (cùng nguồn):
- `dateOfExpiry > dateOfIssue` (nếu có cả hai).
- `dateOfBirth` không ở tương lai; tuổi hợp lý (vd 0–120).
- `idNumber` đúng độ dài theo loại.

---

## 5. Tính confidence

```text
fieldConfidence = base(source) × ocrScore × validatePass
  base(structured) = 0.97, base(ocr) = ocrScore trực tiếp
  validatePass: 1.0 nếu qua mọi rule, giảm theo số rule fail
overallConfidence = Σ(fieldWeight_i × fieldConfidence_i) / Σ(fieldWeight_i)
```
- `fieldWeight` lấy từ `confidence.fieldWeights` của manifest (trường định danh,
  họ tên, ngày sinh trọng số cao hơn).
- Trường `value=null` tính confidence 0 và kéo `overall` xuống → tín hiệu để client
  nhắc kiểm tra tay.

## 6. Quyết định khóa
| ID | Quyết định |
|---|---|
| DEC-050 | Tập trường định nghĩa độc lập với ROI; ROI thuộc manifest |
| DEC-051 | Field thiếu giữ trong schema với value=null, confidence=0 |
| DEC-052 | Cross-check: structured thắng OCR khi lệch; MRZ kiểm bằng checksum |
| DEC-053 | Dữ liệu thẻ quân nhân/đảng viên: mask trong log, hạn chế lưu ảnh |
