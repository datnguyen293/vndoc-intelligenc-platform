# Mẫu tham chiếu — Hộ chiếu Việt Nam #02 (mẫu MỚI / e-passport)

- **Loại:** `passport_vn` (DOC-TYPE-004)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** parser/nhãn (KHÔNG để train).
- **Nguồn:** 1 ảnh trang nhân thân hộ chiếu mẫu mới (2026-06-29).
- **Khác biệt chính so với [mẫu cũ #01](ho-chieu-mau-01.md):** họ/tên **tách 2 trường**;
  định danh là **Số ĐDCN 12 số**; số hộ chiếu **9 ký tự** (1 chữ + 8 số).

## 1. Vùng nhìn (VIZ) — nhãn & giá trị

| Nhãn (VN / EN) | Trường | Giá trị |
|---|---|---|
| Loại / Type | `passportType` | P |
| Mã số / Code | `countryCode` | VNM |
| Số hộ chiếu / Passport No. | `idNumber` | E01828939 |
| **Họ / Surname** | `surname` | NGUYỄN |
| **Chữ đệm và tên / Given names** | `givenNames` | TIẾN ĐẠT |
| Quốc tịch / Nationality | `nationality` | VIỆT NAM / VIETNAMESE |
| Ngày sinh / Date of birth | `dateOfBirth` | 29/03/1988 |
| Giới tính / Sex | `sex` | NAM / M |
| Nơi sinh / Place of birth | `placeOfBirth` | Bắc Giang |
| **Số ĐDCN, CMND / ID No.** | `personalIdNumber` | 024088010438 |
| Ngày cấp / Date of issue | `dateOfIssue` | 20/05/2024 |
| Ngày hết hạn / Date of expiry | `dateOfExpiry` | 20/05/2034 |

→ `fullName` tổng hợp = `surname` + " " + `givenNames` = **NGUYỄN TIẾN ĐẠT**.
→ Mẫu mới **không có** nhãn "Nơi cấp / Place of issue" trên trang này → `issuedBy` để trống.

## 2. MRZ (TD3) — parse + checksum

```
Dòng 1: P<VNMNGUYEN<<TIEN<DAT<<<<<<<<<<<<<<<<<<<<<<<<<
Dòng 2: E018289390VNM8803296M3405204024088010438<<08
```

| Trường MRZ | Vị trí | Giá trị | Giải nghĩa |
|---|---|---|---|
| Document type | L1 1 | P | hộ chiếu |
| Issuing country | L1 3-5 | VNM | Việt Nam |
| Name | L1 6-44 | NGUYEN << TIEN DAT | họ NGUYEN / tên đệm+tên TIEN DAT (**không dấu**) |
| Passport No | L2 1-9 | E01828939 | + check digit `0` |
| Nationality | L2 11-13 | VNM | |
| Date of birth | L2 14-19 | 880329 | → 1988-03-29 (+ cd `6`) |
| Sex | L2 21 | M | Nam |
| Date of expiry | L2 22-27 | 340520 | → 2034-05-20 (+ cd `4`) |
| Personal No | L2 29-40 | 024088010438 | = Số ĐDCN (12 số) (+ cd `0`) |
| Composite cd | L2 44 | 8 | |

→ MRZ tách họ/tên qua dấu `<<` → có thể điền thẳng `surname`/`givenNames` (nhưng
**không dấu** → vẫn lấy bản có dấu từ OCR vùng nhìn).

## 3. JSON kết quả (schema DOC-07)

```json
{
  "documentType": "passport_vn",
  "documentTypeLabel": "Hộ chiếu Việt Nam",
  "fields": {
    "idNumber":         { "value": "E01828939", "confidence": 0.99, "source": "structured" },
    "surname":          { "value": "NGUYỄN", "confidence": 0.97, "source": "ocr" },
    "givenNames":       { "value": "TIẾN ĐẠT", "confidence": 0.97, "source": "ocr" },
    "fullName":         { "value": "NGUYỄN TIẾN ĐẠT", "confidence": 0.97, "source": "ocr" },
    "nationality":      { "value": "Việt Nam", "confidence": 0.99, "source": "structured" },
    "dateOfBirth":      { "value": "1988-03-29", "confidence": 0.99, "source": "structured", "raw": "29/03/1988" },
    "sex":              { "value": "Nam", "confidence": 0.99, "source": "structured" },
    "placeOfBirth":     { "value": "Bắc Giang", "confidence": 0.93, "source": "ocr" },
    "personalIdNumber": { "value": "024088010438", "confidence": 0.98, "source": "structured" },
    "dateOfIssue":      { "value": "2024-05-20", "confidence": 0.95, "source": "ocr", "raw": "20/05/2024" },
    "dateOfExpiry":     { "value": "2034-05-20", "confidence": 0.99, "source": "structured", "raw": "20/05/2034" },
    "issuedBy":         { "value": null, "confidence": 0.0, "source": "ocr" }
  },
  "structuredDataUsed": ["mrz"],
  "warnings": [],
  "errors": []
}
```

## 4. Phát hiện ảnh hưởng thiết kế (bổ sung so với mẫu cũ)

1. **Họ/tên tách 2 trường** ở mẫu mới → thêm `surname`, `givenNames`; `fullName` luôn
   được tổng hợp (mới: ghép; cũ: lấy trực tiếp "Họ và tên"). Plugin nhận **cả 2 layout**.
2. **Định danh "Số ĐDCN, CMND" = 12 số** → thêm nhãn này; regex `^\d{9}$|^\d{12}$` đã phủ.
3. **Số hộ chiếu 1 chữ + 8 số** (E01828939) → nới regex `^[A-Z]\d{7,8}$`.
4. Mẫu mới **không có "Nơi cấp"** trên trang → `issuedBy` cho phép null, không cảnh báo.
5. Phân loại cũ/mới: dựa vào có nhãn "Họ / Surname" + "Chữ đệm và tên" (mới) hay
   "Họ và tên / Full name" (cũ) — nhưng **cùng một `docType`** `passport_vn`, plugin
   tự nhận layout.
