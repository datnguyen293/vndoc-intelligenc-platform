# DOC-05 — Phân loại giấy tờ & Thiết kế plugin

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-03, DOC-04
- **Truy vết:** FR-005, FR-007, FR-008, FR-017, FR-018, NFR-003, NFR-004

## 1. Mục đích

Khóa hai cơ chế: (a) **phân loại** loại giấy tờ, (b) **plugin** mô tả cách bóc tách
từng loại. Đây là phần làm cho hệ thống mở rộng được mà không sửa core.

---

## 2. Phân loại giấy tờ (Document Classification)

### 2.1 Đầu vào / đầu ra
- Đầu vào: ảnh **đã nắn phẳng** về template chuẩn (sau Rectification).
- Đầu ra: `documentType` ∈ danh mục DOC-01, hoặc `unknown`, kèm `confidence ∈ [0,1]`.

### 2.2 Phân loại thuần luật (rule-based, không train — ADR-008, ADR-012)

**Không dùng CNN** (cần dữ liệu train). Phân loại bằng **tín hiệu cứng**, nhanh, không model:

| Tín hiệu | Cách lấy | Gợi ý loại |
|---|---|---|
| Cụm chữ tiêu đề (anchor text) | OCR nhanh 1-2 dòng tiêu đề | "CĂN CƯỚC CÔNG DÂN", "CHỨNG MINH NHÂN DÂN", "GIẤY PHÉP LÁI XE", "THẺ BẢO HIỂM Y TẾ", "HỘ CHIẾU/PASSPORT", "THẺ ĐẢNG VIÊN", "THẺ QUÂN NHÂN" |
| Có vùng QR ở góc trên phải | QR detector | CCCD gắn chip (vs mã vạch) |
| Có MRZ (2 dòng `<<<` ở đáy) | dò pattern MRZ | Hộ chiếu VN |
| Số chữ số định danh | đếm digit của số | CMND 9 số vs 12 số |
| Tỉ lệ khung (aspect ratio) | từ polygon khung | thẻ ID-1 vs hộ chiếu (TD3) |
| Màu nền / hoa văn chủ đạo | histogram vùng | phân biệt nhóm gần giống |

Mỗi plugin khai bảng anchor/luật trong khối `classify` của manifest. Bộ phân loại
OCR nhanh vùng tiêu đề rồi so khớp anchor của từng loại.

### 2.3 Quy tắc quyết định
```text
for mỗi loại đã đăng ký:
    score(loại) = khớp_anchor(tiêu đề) + dấu_hiệu_phụ(QR?, MRZ?, tỉ lệ, số chữ số)
type = argmax(score)
if score(type) < NGƯỠNG:  type = unknown
confidence = chuẩn_hóa(score(type))
```
- Phân biệt khó bằng luật bổ sung:
  - CCCD gắn chip vs mã vạch → có QR mặt trước hay không.
  - **CCCD gắn chip ("CĂN CƯỚC CÔNG DÂN") vs Căn cước 2024 ("CĂN CƯỚC")** → tiêu đề
    có chữ "CÔNG DÂN" hay không.
  - **Căn cước 2024 mặt trước vs mặt sau** → mặt sau có MRZ TD1 + QR + "BỘ CÔNG AN" +
    nhãn "Nơi cư trú"; mặt trước có ảnh chân dung + "Số định danh cá nhân", không QR.

### 2.4 Xử lý `unknown`
- Không nạp plugin; trả JSON với `documentType="unknown"`, `warnings=["khong_nhan_dang_duoc_loai"]`.
- Gợi ý client: chụp lại rõ hơn, đảm bảo căn khung.

---

## 3. Kiến trúc plugin

### 3.1 Nguyên tắc
- Mỗi loại giấy tờ = **một plugin**, định danh bằng `DOC-TYPE` + tên kỹ thuật.
- Plugin **khai báo là chính** (manifest YAML); chỉ dùng code khi cần xử lý đặc biệt.
- Plugin phụ thuộc **plugin contract**, không phụ thuộc ngược vào core (DOC-03 §8).
- Core không hardcode bất kỳ loại nào.

### 3.2 Bố cục thư mục plugin
```text
plugins/
  cccd_chip_front/
    manifest.yaml          # khai báo chính
    template.png           # ảnh template chuẩn (để hiệu chuẩn ROI, tuỳ chọn)
    dictionary/            # từ điển hỗ trợ post-process (tỉnh/thành, dân tộc...)
      provinces.txt
    hooks.py               # (tuỳ chọn) xử lý đặc biệt: parse QR, chuẩn hóa riêng
  passport_vn/
    manifest.yaml
    hooks.py               # parse MRZ TD3
  the_quan_nhan/
    manifest.yaml          # KHUNG CHỜ ẢNH MẪU: field đã khai, ROI để trống
  ...
```

### 3.3 Vòng đời plugin (lifecycle)
```text
Startup:
  Plugin Manager quét thư mục plugins/
  → đọc & validate manifest theo schema
  → biên dịch regex, nạp dictionary, import hooks (nếu có)
  → đăng ký vào Plugin Registry theo documentType
Runtime (mỗi request):
  Classification → documentType
  → Plugin Manager.get(documentType) → trả plugin đã nạp sẵn (warm)
  → Pipeline dùng plugin để: lấy ROI map, đọc structured-data, OCR, validate, normalize
```
- Plugin được nạp **một lần** lúc startup (warm), không nạp lại mỗi request (NFR-001).
- Lỗi một plugin (manifest sai) → log + bỏ qua plugin đó, **không** chết service (NFR-004).

---

## 4. Đặc tả manifest (YAML)

### 4.1 Schema (các khối chính)

```yaml
# manifest.yaml — plugin contract v1
docType: cccd_chip_front          # khớp DOC-TYPE tên kỹ thuật
displayName: "CCCD gắn chip - Mặt trước"
version: "1.0"

template:                          # template chuẩn sau nắn phẳng
  width: 856                       # đơn vị: px chuẩn hoá (vd 10px/mm)
  height: 540
  anchors:                         # điểm/chữ neo để tinh chỉnh lệch ROI
    - id: title
      type: text
      expect: "CĂN CƯỚC CÔNG DÂN"
      roi: { x: 250, y: 40, w: 420, h: 50 }

structuredData:                    # nguồn máy đọc (ưu tiên hơn OCR)
  - kind: qr                       # qr | mrz | barcode
    roi: { x: 600, y: 20, w: 230, h: 230 }
    parser: cccd_qr                # tên parser trong hooks.py / built-in
    mapsTo: [idNumber, oldIdNumber, fullName, dateOfBirth, sex, placeOfResidence, dateOfIssue]

fields:                            # các trường cần bóc tách
  - name: idNumber
    label: "Số"
    source: [structured, ocr]      # thứ tự ưu tiên nguồn
    roi: { x: 300, y: 150, w: 360, h: 50 }
    type: digits
    validate:
      regex: '^\d{12}$'
      required: true
    normalize: [trim, removeSpaces]
    crossCheck: true               # đối chiếu giữa structured và ocr

  - name: fullName
    label: "Họ và tên"
    source: [structured, ocr]
    roi: { x: 300, y: 210, w: 520, h: 60 }
    type: text_vi
    validate: { regex: '^[\p{L}\s]+$', minLen: 2 }
    normalize: [trim, collapseSpaces, upperVi]

  - name: dateOfBirth
    label: "Ngày sinh"
    source: [structured, ocr]
    roi: { x: 300, y: 280, w: 240, h: 50 }
    type: date
    validate: { dateFormat: "dd/MM/yyyy", notFuture: true }
    normalize: [toIsoDate]

confidence:
  fieldWeights:                    # trọng số tính confidence tổng
    idNumber: 0.3
    fullName: 0.3
    dateOfBirth: 0.2
    default: 0.1
```

### 4.2 Kiểu trường (`type`) chuẩn
| type | Ý nghĩa | Hậu xử lý gợi ý |
|---|---|---|
| `digits` | chuỗi số | bỏ khoảng trắng, sửa O↔0, I↔1 |
| `text_vi` | chữ tiếng Việt có dấu | dùng VietOCR, dictionary chỉnh |
| `date` | ngày tháng | chuẩn hóa ISO, kiểm tra hợp lệ |
| `sex` | giới tính | map về `Nam`/`Nữ` |
| `enum` | tập giá trị cố định | khớp gần nhất trong dictionary |
| `mrz` | dòng MRZ | parser TD3 + checksum |
| `code` | mã có cấu trúc (BHYT) | regex theo template |

### 4.3 Nguồn dữ liệu trường (`source`)
- `structured`: lấy từ QR/MRZ/barcode (qua `mapsTo`).
- `ocr`: OCR theo `roi`.
- Khi cả hai: lấy theo thứ tự trong `source` (ưu tiên `structured`), `crossCheck`
  để đối chiếu và điều chỉnh confidence (chi tiết ở DOC-08 §validation).

### 4.4 Hai chiến lược bóc tách (`extraction.strategy`)

Vì ràng buộc không-train (ADR-012), bóc tách dựa trên **luật**, theo một trong hai
chiến lược (có thể phối hợp trong cùng plugin):

| Chiến lược | Cần gì | Hợp với | Cách hoạt động |
|---|---|---|---|
| `roi_fixed` | **1 ảnh mẫu** để đo toạ độ | layout cứng (CMND, CCCD) | OCR đúng ô theo toạ độ tương đối + anchor bù lệch |
| `label_anchored` | **0 ảnh mẫu**, chỉ cần biết nhãn | thẻ nhiều chữ (BHYT, Đảng viên) | OCR theo dòng → tìm nhãn in sẵn → lấy giá trị quanh nhãn |

**`label_anchored` — khai báo field theo nhãn:**
```yaml
extraction:
  strategy: label_anchored
  fields:
    - name: fullName
      labels: ["Họ và tên", "Họ tên"]   # chấp nhận biến thể/viết tắt
      take: after_colon                  # cách lấy giá trị quanh nhãn
      type: text_vi
```

Bộ giá trị `take` chuẩn:
| `take` | Lấy giá trị |
|---|---|
| `after_colon` | phần sau dấu `:` cùng dòng nhãn |
| `after_colon_or_below` | sau `:`; nếu trống thì dòng kế dưới (giá trị xuống dòng) |
| `right_of_label` | cụm chữ nằm bên phải nhãn (cùng hàng, không có dấu `:`) |
| `below_label` | giá trị nằm ở dòng ngay dưới nhãn (bố cục nhãn-trên-giá-trị) |
| `right_of_label_or_below` | bên phải nhãn; nếu trống/tràn thì gộp dòng kế dưới |
| `date_after_label` | dò cụm ngày `dd/MM/yyyy` gần nhãn |
| `vn_date_phrase` | parse "Ngày .. tháng .. năm .." |
| `trailing_digit` | chữ số cuối dòng (vd mức hưởng BHYT) |
| `smart` | thử lần lượt: sau dấu `:` → bên phải → ngay dưới (bền cho nhãn song ngữ "VN/EN:") |

Ghi chú: nhãn **song ngữ ghép "/"** (vd "Số/No", "Họ tên/Full name") được khớp tự
động (token tách theo cả "/"); cụm ngày song ngữ "ngày/date .. tháng/month .. năm/year .."
cũng parse được.

### 4.5 Khóa mở rộng (field & plugin)

Ngoài `validate`/`normalize`, manifest hỗ trợ thêm:

| Khóa | Cấp | Ý nghĩa |
|---|---|---|
| `checks: [warn_if_expired]` | field | rule nghiệp vụ tạo cảnh báo (không chặn). `warn_if_expired`: so `dateOfExpiry` với hôm nay → `da_het_han` |
| `crossCheckProvince: true` | field | đối chiếu 3 số đầu `idNumber` (mã tỉnh) với tỉnh trong địa chỉ → cảnh báo nếu lệch |
| `crossCheck: true` | field | đối chiếu giá trị giữa nguồn `structured` và `ocr` (xem DOC-08 §4) |
| `preprocess: [boost_red_channel_for_id]` | plugin/field | tiền xử lý ảnh đặc thù trước OCR (vd tăng kênh đỏ cho số CMND in đỏ) |
| `required: true/false` | field | trường bắt buộc hay không (mặc định false) |
| `multiline: true` | field | giá trị có thể wrap xuống dòng (vd địa chỉ) → gộp dòng dưới (bỏ dòng ngày/nhãn) |
| `crossChecks: [[a, op, b], ...]` | plugin | kiểm tra logic thứ tự NGÀY giữa các trường (op ∈ `<,<=,>,>=`); sai → cảnh báo `thu_tu_ngay_sai` (vd `[partyJoinDate, "<=", officialDate]`) |

> Nguyên tắc: ưu tiên `structured` (QR/MRZ) → `label_anchored`/`roi_fixed` cho phần
> còn lại. Người vận hành thêm loại giấy tờ chủ yếu bằng **khai nhãn + regex**.

---

## 5. Plugin contract (interface cho hook nâng cao)

Khi manifest không đủ (vd parse QR CCCD, MRZ hộ chiếu), plugin cài `hooks.py`:

```python
class DocumentPlugin(Protocol):
    doc_type: str

    def parse_structured(self, zone_kind: str, raw: bytes | str) -> dict:
        """Parse QR/MRZ/barcode -> {field_name: value}. Trả {} nếu không đọc được."""

    def post_process(self, fields: dict, ctx: "ProcessingContext") -> dict:
        """Chuẩn hóa/đối chiếu riêng cho loại giấy tờ. Tuỳ chọn."""
```

- Core chỉ gọi qua interface; không biết chi tiết bên trong.
- Hook tuỳ chọn — phần lớn plugin chỉ cần manifest.

---

## 6. Hai plugin nội bộ

- **`the_dang_vien`** — **đã có ảnh mẫu**, bóc tách bằng `label_anchored` (không cần
  ROI cố định) → `ready: true`. Xem [samples/the-dang-vien-mau-01.md](samples/the-dang-vien-mau-01.md).
- **`the_quan_nhan`** — **chưa có ảnh mẫu** → `ready: false`. Field đã định nghĩa đủ
  (DOC-08) nên JSON output ổn định, nhưng `labels`/ROI chờ ảnh mẫu thật. Classification
  vẫn nhận dạng được loại qua anchor text; trả `warnings=["plugin_chua_co_mau"]` cho
  tới khi cấu hình xong.

---

## 7. Quyết định khóa

| ID | Quyết định |
|---|---|
| DEC-020 | Phân loại thuần luật trên tín hiệu cứng; KHÔNG dùng CNN (xem ADR-008, ADR-012) |
| DEC-021 | Plugin khai báo bằng manifest YAML; hook code là tuỳ chọn |
| DEC-022 | Plugin nạp warm lúc startup; lỗi 1 plugin không làm chết service |
| DEC-023 | Field nội bộ định nghĩa đủ; ROI map chờ ảnh mẫu thật |
