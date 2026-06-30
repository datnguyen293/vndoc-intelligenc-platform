# DIP OCR Service (skeleton)

Service Python/FastAPI bóc tách giấy tờ tuỳ thân → JSON. Hiện thực theo bộ thiết kế
trong `../docs/` (DOC-03 kiến trúc, DOC-04 ADR, DOC-05 plugin, DOC-07 API).

> **Trạng thái:** SKELETON — khung chạy được đầu-cuối với **stub OCR** (chưa gắn model
> thật). `/extract` trả JSON đúng schema, các trường để `null` kèm cảnh báo
> `ocr_engine_not_implemented`. Việc tiếp theo: cắm PaddleOCR + VietOCR + reader QR/MRZ.

## Cấu trúc

```
service/
  app/
    main.py            # FastAPI app
    settings.py        # cấu hình (env / mặc định)
    api/routes.py      # /extract, /doctypes, /health, /version (DOC-07)
    models/response.py # Pydantic response models (DOC-07)
    core/
      context.py       # ProcessingContext (DOC-03 §6)
      interfaces.py    # Protocol cho từng stage (thay thế được — DOC-03 §8)
    pipeline/engine.py # điều phối 10 stage (DOC-06)
    plugins/
      contract.py      # Manifest + DocumentPlugin protocol (DOC-05)
      manager.py       # nạp manifest YAML lúc startup
    ocr/stub.py        # stub cho detector/classifier/reader/ocr (thay bằng model thật)
  plugins/             # dữ liệu plugin (manifest YAML)
    cccd_2024_back/manifest.yaml
  tests/test_smoke.py
```

## Chạy

```bash
cd service
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Kiểm tra:
```bash
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/doctypes
curl -F image=@/duong/dan/anh.jpg -F docTypeHint=cccd_2024_back \
     http://localhost:8080/api/v1/extract
```

## Xác thực API (`X-API-Key`)

`X-API-Key` là **một chuỗi bí mật dùng chung** do **người quản trị tự đặt**, không
phải hệ thống cấp. Không có database/đăng ký — đúng tinh thần offline LAN (V1).

- Cấu hình bằng biến môi trường **`DIP_API_KEY`** (xem `app/settings.py`).
- **Không đặt** (mặc định) → `/extract` gọi được **không cần header** (tiện dev/test).
- **Có đặt** → client bắt buộc gửi header `X-API-Key: <đúng chuỗi>`, sai/thiếu → `401`.

Triển khai thật:

```bash
# 1) Sinh khóa ngẫu nhiên (làm 1 lần)
python -c "import secrets; print(secrets.token_urlsafe(32))"   # vd: K7zQ...d2F

# 2) Đặt vào service (Windows: set DIP_API_KEY=...; hoặc file .env; hoặc NSSM)
export DIP_API_KEY=K7zQ...d2F
uvicorn app.main:app --port 8080

# 3) Client gửi kèm header
curl -H "X-API-Key: K7zQ...d2F" -F image=@card.jpg -F docTypeHint=the_dang_vien \
     http://localhost:8080/api/v1/extract
```

App Android cấu hình đúng chuỗi này (DOC-09 §8) và gắn header mỗi request. Khi đưa
vào dùng thật nên **bật** để chặn thiết bị lạ trong LAN (NFR-007).

## Backend OCR (`DIP_OCR_BACKEND`)

Chọn engine nhận dạng qua biến môi trường `DIP_OCR_BACKEND` (factory tự fallback):

| Backend | Cài đặt | Đặc điểm |
|---|---|---|
| `vietocr` | `pip install vietocr torch torchvision` | **Tiếng Việt CÓ DẤU** (ADR-004). RapidOCR-det + VietOCR-rec. Chậm hơn (~1s CPU). **Mặc định nếu có.** |
| `rapid` | `pip install rapidocr-onnxruntime` | PP-OCR trên ONNX. Nhanh, nhẹ, nhưng **mất dấu tiếng Việt**. Fallback. |
| `paddle` | `pip install paddleocr paddlepaddle` | Backend nguyên bản ADR-004 (nặng khi cài). |
| `stub` | — | OCR rỗng (chỉ để chạy khung / test API). |

- Offline: đặt file `models/vgg_seq2seq.pth` để VietOCR **không cần tải mạng**.
- Số/ngày chính xác với mọi backend; **dấu tiếng Việt cần `vietocr`**.

## Chống hồi quy khi thêm loại giấy tờ mới (QUAN TRỌNG)

Khi vá thư viện dùng chung (`app/extract/dates.py`, `anchored.py`, `normalize.py`...)
cho một loại MỚI, phải đảm bảo **không làm sai loại CŨ**. Cơ chế:

- `tests/fixtures/ocr/<docType>__<tên-ảnh>.json` — **text OCR thật đã đóng băng**
  (chụp từ VietOCR) cho mỗi ảnh mẫu; tên có tiền tố docType để tránh trùng giữa các loại.
- `tests/test_golden_extract.py` — chạy phân loại + trích xuất trên fixture đó (KHÔNG
  cần model) và so với kết quả vàng. Nhanh, tất định.

Tốc độ test:
- **`pytest`** (mặc định, ~1s): chạy golden + fixture + unit + smoke — **KHÔNG nạp model**.
  Đủ bắt lỗi shared code (golden). Chạy sau **mọi** thay đổi, kể cả không đụng shared.
- **`pytest --runslow`** (~5s): thêm test OCR thật end-to-end (nạp RapidOCR). Chạy khi
  thêm ảnh mẫu/loại mới, hoặc trước cột mốc.
- Thay đổi KHÔNG đụng shared/`app/extract/*` (vd chỉ sửa 1 manifest) → `pytest` nhanh là đủ.

Quy trình:
1. Sửa shared code cho loại mới → `python -m pytest` (golden của loại cũ phải còn xanh).
2. Thêm loại mới: bỏ vài ảnh thật vào `samples/<loại>/`, rồi
   `DIP_OCR_BACKEND=vietocr python -m tools.capture_ocr samples/<loại>/*` để tạo fixture,
   thêm kết quả vàng vào `GOLDEN` trong `test_golden_extract.py`.
3. Nếu **cố ý** đổi hành vi loại cũ → chụp lại fixture + cập nhật GOLDEN có chủ đích.

## Document Rectifier — package `rectifier`

Nắn méo + cắt nền dùng **package `rectifier`** (project `../rectifier`, thuần OpenCV
offline), tích hợp qua `app/cv/build_preprocessors` với **preset `id_card`**. **Nắn-khi-cần**:
ảnh đã phẳng + lấp khung → passthrough (không xê dịch OCR ảnh tốt).

```bash
pip install -e ../rectifier        # cài package (đã có trong requirements.txt)

DIP_CARD_DETECT=true               # bật (mặc định)
DIP_RECTIFY_SEGMENTER=classic|yolo
DIP_YOLO_SEG_WEIGHTS=/path/doc-seg.pt   # nếu dùng yolo (ultralytics, weights cục bộ)
DIP_RECTIFY_CLAHE / DIP_RECTIFY_SHARPEN / DIP_RECTIFY_DENOISE = true|false

# Xem stage (montage) + benchmark (preset id_card):
python -m tools.rectify_debug samples/gplx_pet/tien-dat-meo-2.jpeg /tmp/dbg
python -m tools.rectify_bench samples/gplx_pet/*.webp samples/gplx_pet/*.jpeg
# CLI của chính package:
python -m rectifier in.jpg out.jpg --preset id_card
```

> Nắn sửa **hình học** (méo/nền). Ảnh photo nhiễu nặng (watermark, hoa văn bảo an) OCR
> vẫn có thể lẫn — cần khung căn tốt phía Android + recognition tốt (VietOCR).

## Lộ trình tiếp theo
1. **Tối ưu tốc độ** về < 500 ms (DOC-10): export VietOCR → ONNX/OpenVINO, giới hạn
   OCR theo ROI thay vì cả trang, batch dòng.
2. Thay 2 stub **detect/rectify** bằng OpenCV (khung + nắn hướng — DEC-009).
3. Thêm **classifier thuần luật** (bỏ `docTypeHint`).
4. Thêm reader `cccd_qr` / `mrz_td1` / `mrz_td3` / `bhyt_qr` (loại có structured-data).
5. Sinh nốt manifest cho các loại còn lại (đã có draft trong `../docs/samples/`).
