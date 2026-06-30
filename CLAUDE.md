# CLAUDE.md — ngữ cảnh cho phiên làm việc tiếp theo

Dự án **OCR giấy tờ tuỳ thân Việt Nam** (Android chụp → service Windows offline → JSON).
Trước khi làm: đọc **[HANDOVER.md](HANDOVER.md)** (trạng thái + việc tiếp theo + setup) và
`docs/README.md` (bản đồ tài liệu thiết kế DOC-00→10).

## Quy tắc bắt buộc
- **Không train model** (ADR-012): chỉ OCR pre-trained (VietOCR/RapidOCR) + luật trong
  plugin YAML. **Structured-data-first** (ADR-006): ưu tiên QR/MRZ, OCR bù. **CPU-only**.
- **Thêm loại giấy tờ = thêm 1 `service/plugins/<docType>/manifest.yaml`**, KHÔNG sửa core.
- **Sau khi sửa shared code** (`app/extract/*`, `app/pipeline/*`, `rectifier/`): CHẠY
  `cd service && python -m pytest`. **Golden test phải còn xanh** (chống hồi quy giữa
  các loại). Đổi hành vi có chủ đích → `tools/capture_ocr.py` chụp lại fixture + cập nhật
  `tests/test_golden_extract.py`.
- Trước khi viết loại mới: **lấy ảnh mẫu thật**, chạy OCR thật, đối chiếu, rồi tinh chỉnh
  (ảnh mẫu bị gitignore — anh sẽ cung cấp cục bộ).

## Đang làm dở
🔴 **Structured reader (QR/MRZ/barcode) còn stub** — đây là việc tiếp theo, đi cùng
**CCCD gắn chip**. Định dạng QR/MRZ đã đặc tả trong `docs/samples/*.md`.

## Lệnh
```bash
cd service && source .venv/bin/activate
python -m pytest -q                                  # test nhanh (không model)
DIP_OCR_BACKEND=vietocr python -m tools.ocr_image samples/<docType>/<ảnh>
```

## Phong cách làm việc (theo yêu cầu của anh Đạt)
- Trao đổi tiếng Việt. Làm xong tài liệu thiết kế mới tới code (giai đoạn này đã sang code).
- Sửa thư viện dùng chung cho loại sau **không được làm hỏng loại trước** (→ golden test).
- Thay đổi không đụng shared thì không cần chạy full test (dùng `pytest` nhanh, hoặc
  `--runslow` khi cần real-OCR).
