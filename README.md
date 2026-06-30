# VNDoc Intelligence Platform

Hệ thống **OCR giấy tờ tuỳ thân Việt Nam** — Android chụp ảnh → OCR service trên
Windows (offline) → trả JSON đã bóc tách. Phục vụ đăng ký khách tới làm việc tại đơn vị.

- **Offline hoàn toàn** (yêu cầu an ninh), mục tiêu < 500 ms/ảnh.
- **Không train model**: dùng OCR pre-trained (VietOCR/PaddleOCR) + luật khai báo (plugin).
- **Structured-data-first**: ưu tiên QR/MRZ/barcode, OCR bù phần còn lại.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| [`docs/`](docs/) | Tài liệu thiết kế (DOC-00→10): vision, yêu cầu, kiến trúc, ADR, plugin, API, pipeline, triển khai. |
| [`service/`](service/) | OCR service Python/FastAPI: pipeline, plugin, OCR (VietOCR/RapidOCR), rectifier, tests. |
| [`rectifier/`](rectifier/) | Package nắn chỉnh ảnh (perspective/deskew/crop, thuần OpenCV, offline). |

## Trạng thái (tóm tắt)

- ✅ Khung pipeline đầu-cuối chạy thật: rectification → orientation → classification
  (thuần luật) → OCR (VietOCR có dấu) → label-anchored extraction → JSON.
- ✅ Plugin chạy thật + verify ảnh thật: **Thẻ Đảng viên**, **GPLX PET** (gồm ảnh
  nghiêng/xoay).
- ✅ Lưới **golden test** chống hồi quy (text OCR đóng băng, không cần model).
- 🔜 Đang làm tiếp: **structured reader (QR/MRZ/barcode)** + các loại CCCD/CMND/hộ
  chiếu/BHYT; quality check; tối ưu < 500 ms (OpenVINO); đóng gói Windows Service.

Xem chi tiết: [`docs/README.md`](docs/README.md) · cách chạy/test: [`service/README.md`](service/README.md).

> ⚠️ Ảnh giấy tờ thật (dữ liệu cá nhân) **không** được commit (`.gitignore`, NFR-007).
> Test golden vẫn chạy được vì dùng text OCR đã đóng băng trong `service/tests/fixtures/`.
