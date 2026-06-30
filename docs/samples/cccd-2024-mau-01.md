# Mẫu tham chiếu — Thẻ Căn cước mẫu mới 2024 (2 mặt)

- **Loại:** `cccd_2024_front` (DOC-TYPE-009) + `cccd_2024_back` (DOC-TYPE-010).
- **Phạm vi đã chốt:** nhận **1 ảnh — mặt trước HOẶC mặt sau** (mỗi mặt phân loại &
  bóc tách độc lập); không bắt buộc gửi cả 2 mặt.
- **Bối cảnh:** Thẻ "CĂN CƯỚC" theo Luật Căn cước 2023, cấp từ **01/07/2024**.
- **Mục đích:** ảnh mẫu thật để đánh giá phạm vi + parser (KHÔNG để train).
- **Nguồn:** 1 thẻ Căn cước mới (2 mặt) — 2026-06-29.

## 1. Khác biệt then chốt so với CCCD gắn chip (2021–2024)

| Điểm | CCCD gắn chip (DOC-TYPE-001) | Thẻ Căn cước 2024 (mới) |
|---|---|---|
| Tiêu đề | "CĂN CƯỚC CÔNG DÂN" | **"CĂN CƯỚC"** |
| Vị trí QR | **mặt trước** (góc trên phải) | **mặt sau** (góc trên phải) |
| MRZ | không | **có, TD1 3 dòng** ở mặt sau |
| Quê quán | mặt trước | bỏ; thay bằng "Nơi đăng ký khai sinh" (mặt sau) |
| Nơi cư trú/thường trú | mặt trước | **mặt sau** |
| Hạn dùng | mặt trước | **mặt sau** |
| Mặt trước có đủ để đăng ký? | Có (đủ trường + QR) | **KHÔNG** (thiếu địa chỉ, QR, hạn) |

## 2. Mặt trước — nhãn & giá trị

| Nhãn (VN / EN) | Trường | Giá trị |
|---|---|---|
| Số định danh cá nhân / Personal identification number | `idNumber` | 026099003333 |
| Họ, chữ đệm và tên khai sinh / Full name | `fullName` | LƯƠNG ĐÌNH NAM |
| Ngày, tháng, năm sinh / Date of birth | `dateOfBirth` | 30/12/1999 |
| Giới tính / Sex | `sex` | Nam |
| Quốc tịch / Nationality | `nationality` | Việt Nam |

→ Mặt trước **không có** địa chỉ, quê quán, ngày cấp, hạn dùng, QR.

## 3. Mặt sau — nhãn & giá trị

| Nhãn (VN / EN) | Trường | Giá trị |
|---|---|---|
| Nơi cư trú / Place of residence | `placeOfResidence` | Thôn Dẫn Tự, Tân Phú, Vĩnh Tường, Vĩnh Phúc |
| Nơi đăng ký khai sinh / Place of birth | `placeOfBirth` | Tân Phú, Vĩnh Tường, Vĩnh Phúc |
| Ngày, tháng, năm cấp / Date of issue | `dateOfIssue` | 01/08/2024 |
| Ngày, tháng, năm hết hạn / Date of expiry | `dateOfExpiry` | 30/12/2039 |
| (cơ quan) | `issuedBy` | BỘ CÔNG AN |
| QR (góc trên phải) | structured | (đọc khi chạy thật) |
| MRZ (3 dòng, TD1) | structured | xem §4 |

## 4. MRZ (TD1, 3 dòng × 30 ký tự) — parse + checksum

```
Dòng 1: IDVNM0990033332026099003333<<4
Dòng 2: 9912304M3912302VNM<<<<<<<<<<<2
Dòng 3: LUONG<<DINH<NAM<<<<<<<<<<<<<<<
```

| Trường | Vị trí | Giá trị | Giải nghĩa |
|---|---|---|---|
| Doc type | L1 1-2 | ID | thẻ căn cước |
| Issuing country | L1 3-5 | VNM | Việt Nam |
| Document number | L1 6-14 | 099003333 | số thẻ (9 ký tự) (+ cd) |
| Optional (số định danh) | L1 16-27 | 026099003333 | = số định danh cá nhân (12 số) |
| Date of birth | L2 1-6 | 991230 | → 1999-12-30 (+ cd `4`) |
| Sex | L2 8 | M | Nam |
| Date of expiry | L2 9-14 | 391230 | → 2039-12-30 (+ cd `2`) |
| Nationality | L2 16-18 | VNM | |
| Name | L3 | LUONG << DINH NAM | họ LUONG / tên ĐÌNH NAM (**không dấu**) |

→ MRZ TD1 mặt sau **tự chứa**: số định danh, ngày sinh, giới tính, hạn dùng, tên.
→ 3 số đầu `026` = mã tỉnh **Vĩnh Phúc**, khớp nơi cư trú.

## 5. Nhận xét quan trọng về phạm vi

- **Mặt sau gần như đủ một mình**: có MRZ (số định danh, tên, ngày sinh, giới tính,
  hạn) + QR + **địa chỉ in** (nơi cư trú) + ngày cấp. Mặt trước hầu như **không thêm
  trường dữ liệu** nào (ngoài ảnh chân dung).
- Để đăng ký khách cần **Nơi cư trú (địa chỉ)** → người dùng nên chụp **mặt sau** cho
  mẫu mới (mặt sau đủ một mình: MRZ + QR + địa chỉ + ngày cấp).
- Phạm vi đã chốt (DEC-008): thêm `cccd_2024_front` (DOC-TYPE-009) và `cccd_2024_back`
  (DOC-TYPE-010); nhận 1 ảnh mặt trước HOẶC mặt sau. Cần parser `mrz_td1` (mặt sau) và
  xác định lại `cccd_qr` cho QR mặt sau (có thể khác QR mặt trước CCCD gắn chip).

## 6. JSON kết quả MẶT SAU (schema DOC-07)

API stateless, mỗi request 1 mặt (DEC-042). Mặt sau tự chứa gần đủ trường nhờ MRZ +
QR + địa chỉ in. (Mặt trước `cccd_2024_front` chỉ trả tập rút gọn: `idNumber`,
`fullName`, `dateOfBirth`, `sex`, `nationality`.)

```json
{
  "documentType": "cccd_2024_back",
  "documentTypeLabel": "Căn cước 2024 - Mặt sau",
  "fields": {
    "idNumber":         { "value": "026099003333", "confidence": 0.99, "source": "structured" },
    "fullName":         { "value": "LƯƠNG ĐÌNH NAM", "confidence": 0.98, "source": "ocr" },
    "dateOfBirth":      { "value": "1999-12-30", "confidence": 0.99, "source": "structured", "raw": "30/12/1999" },
    "sex":              { "value": "Nam", "confidence": 0.99, "source": "structured" },
    "nationality":      { "value": "Việt Nam", "confidence": 0.97, "source": "ocr" },
    "placeOfResidence": { "value": "Thôn Dẫn Tự, Tân Phú, Vĩnh Tường, Vĩnh Phúc", "confidence": 0.90, "source": "ocr" },
    "placeOfBirth":     { "value": "Tân Phú, Vĩnh Tường, Vĩnh Phúc", "confidence": 0.91, "source": "ocr" },
    "dateOfIssue":      { "value": "2024-08-01", "confidence": 0.94, "source": "ocr", "raw": "01/08/2024" },
    "dateOfExpiry":     { "value": "2039-12-30", "confidence": 0.99, "source": "structured", "raw": "30/12/2039" },
    "issuedBy":         { "value": "Bộ Công an", "confidence": 0.95, "source": "ocr" }
  },
  "structuredDataUsed": ["mrz_td1"],
  "warnings": [],
  "errors": []
}
```
