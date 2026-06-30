# DOC-06 — Pipeline OCR & Bóc tách dữ liệu

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-04, DOC-05
- **Truy vết:** FR-002, FR-003, FR-004, FR-006, FR-008, FR-009, NFR-001, NFR-008

## 1. Mục đích

Đặc tả chi tiết các bước xử lý ảnh → text → trường dữ liệu, kèm **ngân sách thời
gian 500 ms** trên CPU.

---

## 2. Sơ đồ pipeline

```text
Ảnh gốc
  │
  ▼  [S1] Image Quality Check ──(reject)──▶ trả "chụp lại"
  ▼  [S2] Document Detection (classical CV)
  ▼  [S3] Perspective Rectification → ảnh template chuẩn
  ▼  [S4] Classification → documentType (+ nạp plugin)
  ▼  [S5] Structured-Data Reader (QR/MRZ/barcode) ── nếu plugin khai báo
  ▼  [S6] ROI Crop (theo manifest, có hiệu chỉnh anchor)
  ▼  [S7] OCR (PaddleOCR det → VietOCR rec) cho ROI chưa có giá trị
  ▼  [S8] Validation + Normalization + Cross-check
  ▼  [S9] Tính confidence
  ▼  [S10] Response Builder → JSON
```

---

## 3. Chi tiết từng stage

### S1 — Image Quality Check
- **Blur:** variance của Laplacian; dưới ngưỡng → mờ.
- **Brightness/Contrast:** thống kê histogram; quá tối/sáng/loá → cảnh báo.
- **Glare:** tỉ lệ pixel bão hòa (cụm sáng trắng) lớn → loá.
- Quá kém → trả sớm `errors=["anh_qua_kem"]` + chỉ số, không chạy tiếp.
- Mục tiêu: rất nhanh (~5 ms), tránh tốn công cho ảnh hỏng.

### S2 — Document Detection (classical CV, ADR-007)
1. Resize ảnh về cạnh dài ~1280 px (giảm tải).
2. Grayscale → Gaussian blur → Canny/adaptive threshold.
3. Tìm contour, lọc tứ giác lồi diện tích lớn nhất ≈ khung giấy tờ.
4. Trả 4 góc (polygon). Thất bại → fallback segmentation nhẹ hoặc dùng cả ảnh.

**Document Rectifier** — dùng **package `rectifier`** (project riêng `../rectifier`,
thuần OpenCV offline), tích hợp qua `app/cv/build_preprocessors` với **preset `id_card`**:
```
Image → Segmentation → Largest Mask → Polygon Fitting → Corner Refinement →
Perspective → Auto Rotate → Adaptive Padding → Deskew → CLAHE → Sharpen → Output
```
- **Segmenter** (pluggable): `classic` (OpenCV: Otsu+Canny+morphology, có GrabCut
  fallback) hoặc `yolo` (YOLOv11-seg, cần weights cục bộ — `DIP_YOLO_SEG_WEIGHTS`,
  fallback classic). Cấu hình `DIP_RECTIFY_SEGMENTER`.
- **Preset `id_card`**: ràng buộc tỉ lệ thẻ ID-1 (1.2–2.3), auto-rotate landscape,
  nắn-khi-cần (skip_fill 0.88 / skip_skew 4°).
- Bật/tắt: `DIP_CARD_DETECT`. Enhance: `DIP_RECTIFY_CLAHE/SHARPEN/DENOISE`.
- **Debug viz** `tools/rectify_debug.py` (montage stages) + **benchmark**
  `tools/rectify_bench.py`. Logic nắn có **unit test riêng** trong `../rectifier`;
  service có test tích hợp `tests/test_rectify_integration.py`.

**Nắn-khi-cần (mặc định BẬT, `DIP_CARD_DETECT`):** detector chỉ trả polygon khi ảnh
THỰC SỰ cần nắn — nếu thẻ **đã phẳng + lấp ≥88% khung và skew ≤4°** thì trả None
(passthrough, **không xê dịch OCR** trên ảnh vốn đã tốt). Chỉ ảnh **chụp nghiêng/nhiều
nền** mới được warp. Nhờ vậy bật mặc định an toàn: ảnh tốt giữ nguyên kết quả, ảnh méo
được nắn phẳng. Bước **resize-cap** luôn chạy độc lập.

> Lưu ý: nắn sửa **hình học** (méo/nền). Với ảnh photo nhiễu nặng (watermark, hoa văn
> bảo an, glare), OCR vẫn có thể lẫn — đó là giới hạn chất lượng ảnh, cần khung căn tốt
> phía Android (DOC-09) + recognition tốt (VietOCR).

### S3 — Perspective Rectification + Orientation
- Warp perspective 4 góc → kích thước template chuẩn của loại (sau khi biết loại ở
  S4 có thể tinh chỉnh; bản đầu dùng tỉ lệ ID-1 hoặc TD3).
- **Chuẩn hóa hướng ảnh (0/90/180/270°) — DEC-009:** ảnh chụp thường bị xoay 90°/180°
  (vd thẻ BHYT chụp dọc → chữ chạy dọc).
  - *Hiện thực (đã làm):* `OrientingOcr` bọc quanh OCR engine — thử 4 chiều và **chấm
    điểm bằng chính OCR** (confidence × ưu tiên box chữ NGANG). Chiều đúng có chữ ngang
    + confidence cao nhất. **Thích ứng:** ảnh thẳng (0° đã đủ tốt) chỉ OCR 1 lần; ảnh
    xoay mới thử thêm. Bật/tắt bằng `DIP_AUTO_ORIENT`.
  - Phương án nâng cao sau: angle classifier riêng (PP cls) để khỏi OCR 4 lần.
- Chuẩn hóa độ phân giải ROI ổn định (vd 10 px/mm) để toạ độ ROI trong manifest khớp.
- Cân bằng sáng nhẹ (CLAHE) nếu cần cho OCR.

### S4 — Classification
- Theo DOC-05 §2 (thuần luật trên tín hiệu cứng, không train).
- **Tối ưu hiện thực:** OCR (S7) được chạy **một lần trước**, và bộ phân loại đọc
  **chính text OCR đó** để khớp anchor (vd "THẺ ĐẢNG VIÊN") → vừa tránh OCR 2 lần,
  vừa cho phép bỏ `docTypeHint`. `docTypeHint` nếu có vẫn được ưu tiên.
- Nạp plugin tương ứng từ Plugin Registry (đã warm).

### S5 — Structured-Data Reader (ADR-006)
Chạy theo khai báo `structuredData` trong manifest:

| Loại | Thư viện gợi ý | Ghi chú |
|---|---|---|
| **QR CCCD** (CCCD gắn chip mặt trước; Căn cước 2024 mặt sau) | OpenCV QRCodeDetector / pyzbar / zxing-cpp | parser `cccd_qr`: 7 trường ngăn cách `\|` |
| **QR BHYT** (mặt thông tin) | pyzbar/zxing | parser **`bhyt_qr`** (định dạng **khác** CCCD QR — cần xác định trên thẻ thật) |
| **MRZ TD3** (hộ chiếu, 2 dòng × 44) | OCR vùng MRZ + parser `mrz_td3` | có **checksum** tự kiểm |
| **MRZ TD1** (Căn cước 2024 mặt sau, 3 dòng × 30) | OCR vùng MRZ + parser `mrz_td1` | có **checksum**; cấu trúc khác TD3 |
| **Barcode** (loại khác) | pyzbar/zxing | đọc mã thẻ nếu có |

> Lưu ý: mỗi loại QR có parser riêng — `cccd_qr` (CCCD/Căn cước) và `bhyt_qr` (BHYT)
> **không** dùng chung định dạng. Định dạng `bhyt_qr` cần xác định trên thẻ BHYT thật.

- **QR CCCD format** (mặt trước): chuỗi gồm các trường ngăn cách bằng `|`:
  `số CCCD | số CMND cũ | họ tên | ngày sinh | giới tính | nơi thường trú | ngày cấp`.
  Đọc QR là gần như tuyệt đối → điền thẳng vào field, OCR chỉ để cross-check.
- **MRZ TD3** (2 dòng 44 ký tự): chứa số hộ chiếu, quốc tịch, ngày sinh, giới tính,
  ngày hết hạn, họ tên; có **check digit** để sửa lỗi đọc.
- Nếu đọc structured thành công, các field `mapsTo` được đánh dấu "đã có nguồn", S7
  **bỏ qua OCR** các ROI đó (trừ khi `crossCheck: true`).

### S6 — ROI Crop (có hiệu chỉnh anchor)
- Cắt từng ROI theo toạ độ manifest trên ảnh template chuẩn.
- Dùng **anchor** (chữ neo như tiêu đề, nhãn "Họ và tên") để bù lệch nhỏ do nắn ảnh:
  dò vị trí anchor thực tế → dịch toàn bộ ROI map một offset → bền hơn với sai số.
- Thêm margin quanh ROI để không cắt cụt ký tự có dấu.

### S7 — OCR (PaddleOCR det + VietOCR rec, ADR-004)
Cho mỗi ROI chưa có giá trị từ structured:
1. **Text detection** (PaddleOCR DB) trên ROI → các box dòng chữ.
2. **Recognition** (VietOCR) cho từng dòng → text + score.
3. Ghép kết quả theo thứ tự đọc; gắn `ocrConfidence` trung bình theo ký tự/dòng.
- Tối ưu: **batch nhiều ROI** vào một lần recognition để tận dụng CPU.
- Áp **dictionary** theo trường (vd danh sách tỉnh/thành, dân tộc) để sửa lỗi gần đúng.

### S8 — Validation + Normalization + Cross-check
- Theo manifest + DOC-08: regex, độ dài, định dạng ngày, checksum.
- **Cross-check** khi field có cả nguồn structured và ocr:
  - khớp → confidence cao.
  - lệch → ưu tiên `structured` (QR/MRZ chính xác hơn), ghi `warnings`.
- Chuẩn hóa: ngày → ISO `YYYY-MM-DD`, giới tính → `Nam/Nữ`, gộp khoảng trắng, viết
  hoa tiếng Việt đúng chuẩn.

### S9 — Confidence
- `fieldConfidence` = hợp nhất nguồn (structured ưu tiên) × điểm OCR × kết quả validate.
- `overallConfidence` = trung bình có trọng số theo `confidence.fieldWeights` trong manifest.

### S10 — Response Builder
- Gom thành JSON thống nhất (schema ở DOC-07), kèm `timings`, `warnings`, `errors`.

---

## 4. Ngân sách thời gian (mục tiêu < 500 ms, CPU i7-14700)

| Stage | Mục tiêu (ms) | Ghi chú |
|---|---|---|
| S1 Quality check | 5 | thuần CV |
| S2 Detection | 25 | classical CV |
| S3 Rectification | 15 | warp + CLAHE |
| S4 Classification | 20 | thuần luật trên tín hiệu cứng |
| S5 Structured (QR/MRZ) | 10–20 | rất nhanh, gần tuyệt đối |
| S6 ROI crop | 5 | |
| S7 OCR (det+rec) | 200–300 | phần nặng nhất; batch ROI |
| S8 Validate/normalize | 5 | |
| S9 Confidence | 2 | |
| S10 Response | 3 | |
| **Tổng** | **~290–400 ms** | còn biên dưới 500 ms |

Ghi chú tối ưu để giữ ngân sách:
- CCCD gắn chip đọc được QR → **bỏ phần lớn OCR** → nhanh hơn nhiều.
- OCR chỉ chạy trên ROI nhỏ, không cả trang.
- Model chạy OpenVINO (CPU Intel), warm sẵn, batch recognition.
- Nếu recognition transformer chậm trên CPU: cân nhắc VietOCR seq2seq nhẹ, hoặc
  INT8 quantization (kiểm chứng độ chính xác trước).

---

## 5. Xử lý lỗi & suy giảm mềm (graceful degradation)

| Tình huống | Hành vi |
|---|---|
| Không phát hiện khung (S2) | thử OCR trên cả ảnh; nếu vẫn fail → `unknown` + cảnh báo |
| Không phân loại được (S4) | trả `unknown`, không nạp plugin |
| QR/MRZ đọc lỗi (S5) | fallback hoàn toàn sang OCR cho các field đó |
| Một ROI OCR rỗng | field để trống + `warnings` cho field đó, không chặn cả request |
| Validate fail một field | giữ giá trị thô + `errors` cho field, vẫn trả các field khác |

Nguyên tắc: **không vì một trường lỗi mà bỏ cả kết quả** — trả tối đa những gì đọc được.

## 6. Quyết định khóa

| ID | Quyết định |
|---|---|
| DEC-030 | OCR chỉ chạy trên ROI chưa có nguồn structured |
| DEC-031 | Khi structured và OCR lệch, ưu tiên structured + ghi cảnh báo |
| DEC-032 | Pipeline suy giảm mềm: lỗi một phần không bỏ cả kết quả |
| DEC-033 | Dùng anchor text để bù lệch ROI sau nắn ảnh |
