# samples/ — ảnh mẫu (KHÔNG đưa lên git)

Thư mục này chứa ảnh giấy tờ tuỳ thân **thật** dùng để phát triển/kiểm thử OCR.

> ⚠️ **Dữ liệu cá nhân thật** (họ tên, số định danh, ngày sinh, địa chỉ của người
> thật) → các file ảnh (`*.jpg/jpeg/png/webp`) **bị `.gitignore`**, không commit
> (NFR-007). Chỉ giữ cục bộ trên máy.

## Cấu trúc theo `docType`
```
samples/
  the_dang_vien/       # Thẻ Đảng viên
  gplx_pet/            # GPLX PET
  cccd_chip_front/     # CCCD gắn chip - mặt trước
  cccd_barcode_front/  # CCCD mã vạch - mặt trước
  ...                  # mỗi loại một thư mục (đúng tên docType)
```

## Dùng để test
- Test golden (`tests/test_golden_extract.py`) chạy trên **text OCR đã đóng băng**
  (`tests/fixtures/ocr/*.json`) — KHÔNG cần ảnh → vẫn chạy được sau khi clone.
- Test real-OCR (`--runslow`) cần ảnh thật trong các thư mục này; thiếu ảnh sẽ **skip**.
- Thêm ảnh mới: bỏ vào `samples/<docType>/` rồi
  `DIP_OCR_BACKEND=vietocr python -m tools.capture_ocr samples/<docType>/<ảnh>` để tạo fixture.
