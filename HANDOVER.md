# HANDOVER — chuyển giao sang máy khác để tiếp tục

Tài liệu bàn giao trạng thái dự án **VNDoc Intelligence Platform** (OCR giấy tờ tuỳ
thân VN). Đọc kèm: [`README.md`](README.md), [`docs/README.md`](docs/README.md),
[`service/README.md`](service/README.md).

Repo: `git@github.com:datnguyen293/vndoc-intelligenc-platform.git`

---

## 1. Setup trên máy mới

```bash
git clone git@github.com:datnguyen293/vndoc-intelligenc-platform.git
cd vndoc-intelligenc-platform/service

# Khuyến nghị Python 3.11 (dev cũ chạy 3.9 nên phải thêm eval_type_backport)
python3.11 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt        # gồm: fastapi, pydantic, rapidocr-onnxruntime, -e ../rectifier
pip install pytest httpx               # để chạy test
# Nếu BẮT BUỘC dùng Python 3.9: pip install eval_type_backport

# OCR tiếng Việt CÓ DẤU (khuyến nghị) — nặng, lần đầu tải weights (cần Internet):
pip install vietocr torch torchvision
```

Kiểm tra nhanh:
```bash
python -m pytest -q          # ~1s, KHÔNG cần model → phải PASS ngay sau clone
DIP_OCR_BACKEND=vietocr uvicorn app.main:app --port 8080   # chạy API
```

### ⚠️ Ảnh mẫu KHÔNG có trong repo
Ảnh giấy tờ thật bị `.gitignore` (dữ liệu cá nhân, NFR-007). Hệ quả:
- **Test golden + unit + smoke**: chạy được ngay (dùng text OCR đóng băng ở
  `service/tests/fixtures/ocr/*.json`).
- **Test real-OCR** (`pytest --runslow`): sẽ **skip** vì thiếu ảnh.
- Muốn chạy lại trên ảnh thật: copy ảnh vào `service/samples/<docType>/` (vd
  `gplx_pet/`, `the_dang_vien/`) rồi
  `DIP_OCR_BACKEND=vietocr python -m tools.capture_ocr samples/<docType>/<ảnh>`.

---

## 2. Hiện trạng (tính tới lần bàn giao)

### Pipeline 10 stage
| Stage | Trạng thái |
|---|---|
| Quality check | 🔴 **Stub** (luôn pass) — cần đo mờ/sáng/loá (FR-002) |
| Document rectification | 🟢 Thật — package `rectifier` (preset `id_card`), "nắn-khi-cần" |
| Orientation 0/90/180/270 | 🟢 Thật — `OrientingOcr` (chấm điểm bằng OCR) |
| Classification | 🟢 Thật — `RuleClassifier` theo anchor, không train |
| **Structured reader (QR/MRZ/barcode)** | 🔴 **Stub** — chưa đọc gì (lỗ hổng lớn nhất) |
| OCR (detect+recognize) | 🟢 Thật — VietOCR / RapidOCR / stub |
| Field extraction (label-anchored) | 🟢 Thật, mạnh |
| Response builder | 🟢 Thật (+ timings) |
| `returnImage`, `dictFix` (từ điển) | 🟡/🔴 chưa làm |

### Plugin theo loại (10 loại trong danh mục, xem `docs/01`)
- ✅ **Chạy thật + verify ảnh thật**: `the_dang_vien`, `gplx_pet` (gồm méo + xoay 90/180/270).
- 🟡 `cccd_2024_back`: có manifest nhưng **cần structured reader** (QR+MRZ) mới đúng.
- ❌ Chưa có plugin: CCCD gắn chip/mã vạch, CMND 9, hộ chiếu, BHYT, căn cước 2024 mặt
  trước, thẻ quân nhân (chưa có ảnh mẫu).

### Test: 33 (`--runslow`)
- **Golden 11 ca** (`tests/test_golden_extract.py`): chạy bộ trích xuất trên **text OCR
  đóng băng** → chống hồi quy shared code, KHÔNG cần model.
- Real-OCR 5 (slow, cần ảnh + rapidocr). Unit/integration/smoke còn lại.

---

## 3. VIỆC TIẾP THEO (ưu tiên)

**P0 — đang dở, làm trước:**
1. 🔴 **Structured reader thật** (ADR-006): `cccd_qr` (CCCD/Căn cước, 7 trường ngăn `|`),
   `mrz_td3` (hộ chiếu), `mrz_td1` (căn cước 2024 mặt sau), `bhyt_qr`. Định dạng đã đặc
   tả trong `docs/samples/*.md`. Thư viện: `pyzbar`/`zxing-cpp` (QR), parser MRZ tự viết.
2. Viết plugin + verify **CCCD gắn chip** (anh đã để folder `samples/cccd_chip_front/`).

**P1:** quality check (FR-002); từ điển tỉnh/CSYT cho `dictFix`; implement `returnImage`.

**P2 (sản phẩm hóa, khi sang máy đích Windows i7-14700):** export VietOCR→ONNX/OpenVINO
cho < 500ms; đóng gói Windows Service (NSSM) + bundle model offline; logging/metrics mask
số định danh; Android SDK (DOC-09, chưa bắt đầu).

---

## 4. Quy ước & quyết định cốt lõi (đừng làm trái)

- **Không train** model nào (ADR-012): chỉ OCR pre-trained + luật khai báo trong plugin (YAML).
- **Structured-data-first** (ADR-006): có QR/MRZ thì ưu tiên, OCR bù.
- **CPU-only** (ADR-002): GPU AMD không dùng; tốc độ đo trên CPU; máy đích i7-14700.
- **Backend OCR** (`DIP_OCR_BACKEND`): `vietocr` (có dấu, khuyến nghị) · `rapid` (nhanh,
  **mất dấu** — chỉ hợp cho trường số/ngày) · `stub`.
- **Plugin** = 1 file `manifest.yaml` (`service/plugins/<docType>/`): classify anchors +
  fields (label-anchored, take/normalize/validate) + crossChecks. Thêm loại = thêm
  manifest, KHÔNG sửa core (`docs/05`).
- **CHỐNG HỒI QUY (bắt buộc):** sửa shared code (`app/extract/*`, `app/pipeline/*`,
  rectifier) → chạy `python -m pytest` (golden phải còn xanh). Đổi hành vi CÓ CHỦ ĐÍCH →
  `tools/capture_ocr.py` chụp lại fixture + cập nhật `GOLDEN`.
- **Tốc độ test:** `pytest` mặc định nhanh (không model); `pytest --runslow` mới chạy
  real-OCR (`conftest.py` có cờ `--runslow`).

## 5. Gotchas (đã vấp)
- **bash cwd**: luôn `cd service` trước khi chạy lệnh.
- **VietOCR** lần đầu tải weights (`vgg_seq2seq.pth`) — cần Internet; máy đích offline
  phải copy sẵn weights (đặt path qua config rectifier hoặc cache VietOCR).
- **RapidOCR mất dấu** tiếng Việt; **VietOCR giữ dấu**. Golden/verify dùng VietOCR.
- **Ảnh photo nhiễu nặng** (watermark, hoa văn bảo an) OCR vẫn lẫn dù đã nắn đúng hình học.
- **Dữ liệu cá nhân**: ảnh bị gitignore; nhưng text (fixtures/golden/docs) CÓ data thật
  — cân nhắc nếu chia sẻ rộng.

## 6. Lệnh hay dùng
```bash
cd service && source .venv/bin/activate
# OCR 1 ảnh
DIP_OCR_BACKEND=vietocr python -m tools.ocr_image samples/gplx_pet/tien-dat.jpeg
# Xem ảnh đã nắn (montage các stage)
python -m tools.rectify_debug samples/gplx_pet/tien-dat-meo-2.jpeg /tmp/dbg
# Test
python -m pytest -q            # nhanh
python -m pytest -q --runslow  # đầy đủ (cần ảnh + rapidocr)
```
