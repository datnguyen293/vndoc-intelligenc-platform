# Mẫu tham chiếu — Hộ chiếu Việt Nam #01

- **Loại:** `passport_vn` (DOC-TYPE-004)
- **Mục đích:** ảnh mẫu thật để **hiệu chỉnh** parser MRZ + nhãn (KHÔNG để train).
- **Nguồn:** 1 ảnh trang nhân thân hộ chiếu do người dùng cung cấp (2026-06-29).
- **Lưu ý:** hộ chiếu **mẫu cũ** (TD3, trường "Số GCMND" 9 số). Mẫu mới (2022+) có
  "Số định danh cá nhân" 12 số — plugin nhận cả hai.

## 1. Quan sát căn chỉnh

- Ảnh đúng chiều, trang nhân thân nằm ngang (landscape).
- Bố cục: ảnh chân dung trái; vùng nhìn (VIZ) **nhãn song ngữ Việt/Anh, nhãn-trên-
  giá-trị, 2 cột**; dưới cùng là **MRZ 2 dòng (TD3, 44 ký tự/dòng)**.
- Chiến lược: **MRZ là nguồn structured chính (có checksum)** → VIZ (OCR) bù trường
  MRZ không có (nơi sinh, ngày cấp, nơi cấp) + lấy tên **có dấu**.

## 2. Vùng nhìn (VIZ) — nhãn & giá trị

| Nhãn (VN / EN) | Trường | Giá trị |
|---|---|---|
| Loại / Type | `passportType` | P |
| Mã số / Code | `countryCode` | VNM |
| Số hộ chiếu / Passport No | `idNumber` | B7849474 |
| Họ và tên / Full name | `fullName` | NGUYỄN TIẾN ĐẠT |
| Quốc tịch / Nationality | `nationality` | VIỆT NAM / VIETNAMESE |
| Ngày sinh / Date of birth | `dateOfBirth` | 29/03/1988 |
| Nơi sinh / Place of birth | `placeOfBirth` | BẮC GIANG |
| Giới tính / Sex | `sex` | NAM / M |
| Số GCMND / ID card No | `personalIdNumber` | 121647952 |
| Ngày cấp / Date of issue | `dateOfIssue` | 13/05/2013 |
| Có giá trị đến / Date of expiry | `dateOfExpiry` | 13/05/2023 |
| Nơi cấp / Place of issue | `issuedBy` | Cục Quản lý xuất nhập cảnh |

## 3. MRZ (TD3) — parse + checksum

```
Dòng 1: P<VNMNGUYEN<<TIEN<DAT<<<<<<<<<<<<<<<<<<<<<<<<<
Dòng 2: B7849474<6VNM8803296M2305134121647952<<<<<50
```

| Trường MRZ | Vị trí | Giá trị | Giải nghĩa |
|---|---|---|---|
| Document type | L1 1 | P | hộ chiếu |
| Issuing country | L1 3-5 | VNM | Việt Nam |
| Name | L1 6-44 | NGUYEN << TIEN DAT | họ NGUYEN, tên TIEN DAT (**không dấu**) |
| Passport No | L2 1-9 | B7849474 | + check digit `6` |
| Nationality | L2 11-13 | VNM | |
| Date of birth | L2 14-19 | 880329 | → 1988-03-29 (+ cd `6`) |
| Sex | L2 21 | M | Nam |
| Date of expiry | L2 22-27 | 230513 | → 2023-05-13 (+ cd `4`) |
| Personal No | L2 29-42 | 121647952 | = Số GCMND (+ cd `5`) |
| Composite cd | L2 44 | 0 | |

→ MRZ **khớp** vùng nhìn ở mọi trường có cả hai nguồn → confidence cao.
→ Tên MRZ không dấu → **lấy tên có dấu từ OCR vùng nhìn**.

## 4. JSON kết quả (schema DOC-07)

```json
{
  "documentType": "passport_vn",
  "documentTypeLabel": "Hộ chiếu Việt Nam",
  "fields": {
    "idNumber":         { "value": "B7849474", "confidence": 0.99, "source": "structured" },
    "fullName":         { "value": "NGUYỄN TIẾN ĐẠT", "confidence": 0.97, "source": "ocr" },
    "nationality":      { "value": "Việt Nam", "confidence": 0.99, "source": "structured" },
    "dateOfBirth":      { "value": "1988-03-29", "confidence": 0.99, "source": "structured", "raw": "29/03/1988" },
    "sex":              { "value": "Nam", "confidence": 0.99, "source": "structured" },
    "placeOfBirth":     { "value": "Bắc Giang", "confidence": 0.93, "source": "ocr" },
    "personalIdNumber": { "value": "121647952", "confidence": 0.98, "source": "structured" },
    "dateOfIssue":      { "value": "2013-05-13", "confidence": 0.95, "source": "ocr", "raw": "13/05/2013" },
    "dateOfExpiry":     { "value": "2023-05-13", "confidence": 0.99, "source": "structured", "raw": "13/05/2023" },
    "issuedBy":         { "value": "Cục Quản lý xuất nhập cảnh", "confidence": 0.92, "source": "ocr" }
  },
  "structuredDataUsed": ["mrz"],
  "warnings": [],
  "errors": []
}
```
> Hộ chiếu này đã **hết hạn 13/05/2023** → validation nên gắn cảnh báo `da_het_han`
> (so `dateOfExpiry` với ngày hiện tại), không chặn kết quả.

## 5. Phát hiện ảnh hưởng thiết kế

1. **Tên MRZ không dấu** → `fullName` ưu tiên OCR (có dấu); MRZ để cross-check tên ASCII.
2. **Trường định danh 2 dạng:** cũ "Số GCMND / ID card No" (9 số), mới "Số định danh
   cá nhân / Personal No" (12 số) → regex `^\d{9}$|^\d{12}$`, khớp cả 2 nhãn.
3. **Nhãn song ngữ + bố cục nhãn-trên-giá-trị, 2 cột** → `take: below_label`,
   `labels` gồm cả tiếng Việt và tiếng Anh.
4. **Cảnh báo hết hạn:** thêm rule so `dateOfExpiry` với ngày hiện tại → `da_het_han`.
5. Nên thêm trường phụ `passportType` (P) và `countryCode` (VNM) — tuỳ chọn.

## 6. Draft plugin Hộ chiếu (MRZ-first + label-anchored)

```yaml
docType: passport_vn
displayName: "Hộ chiếu Việt Nam"
classify:
  anchors: ["HỘ CHIẾU", "PASSPORT"]
  signals: [has_mrz_td3]

structuredData:
  - kind: mrz
    format: td3
    parser: mrz_td3            # parse + verify check digits
    mapsTo: [idNumber, nationality, fullName, dateOfBirth, sex, dateOfExpiry, personalIdNumber]

extraction:
  strategy: label_anchored
  fields:
    - name: idNumber
      labels: ["Số hộ chiếu", "Passport No"]
      take: below_label
      source: [structured, ocr]
      type: code
      validate: { regex: '^[A-Z]\d{7,8}$' }   # cũ 7 số (B7849474) / mới 8 số (E01828939)
    - name: fullName
      labels: ["Họ và tên", "Full name"]
      take: below_label
      source: [ocr, structured]      # OCR trước để giữ dấu tiếng Việt
      type: text_vi
      crossCheck: true               # đối chiếu với tên MRZ (bỏ dấu)
    - name: nationality
      labels: ["Quốc tịch", "Nationality"]
      take: below_label
      source: [structured, ocr]
      type: text_vi
    - name: dateOfBirth
      labels: ["Ngày sinh", "Date of birth"]
      take: date_after_label
      source: [structured, ocr]
      type: date
    - name: placeOfBirth
      labels: ["Nơi sinh", "Place of birth"]
      take: below_label
      type: text_vi
      normalize: [dictFix]
    - name: sex
      labels: ["Giới tính", "Sex"]
      take: below_label
      source: [structured, ocr]
      type: sex
    - name: personalIdNumber
      labels: ["Số GCMND", "ID card No", "Số định danh cá nhân", "Personal No"]
      take: below_label
      source: [structured, ocr]
      type: code
      validate: { regex: '^\d{9}$|^\d{12}$' }
    - name: dateOfIssue
      labels: ["Ngày cấp", "Date of issue"]
      take: date_after_label
      type: date
    - name: dateOfExpiry
      labels: ["Có giá trị đến", "Date of expiry"]
      take: date_after_label
      source: [structured, ocr]
      type: date
      checks: [warn_if_expired]
    - name: issuedBy
      labels: ["Nơi cấp", "Place of issue"]
      take: below_label
      type: text_vi
```
