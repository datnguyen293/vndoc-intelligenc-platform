# Hệ thống OCR Giấy tờ tuỳ thân — Tài liệu thiết kế

Bộ tài liệu thiết kế chi tiết cho hệ thống bóc tách thông tin cá nhân từ giấy tờ
tuỳ thân của công dân Việt Nam tới làm việc tại đơn vị bộ đội, phục vụ đăng ký
khách nhanh chóng.

- **Tên dự án (kỹ thuật):** Document Intelligence Platform (DIP)
- **Trạng thái:** Giai đoạn thiết kế — chưa code
- **Ngày bắt đầu:** 2026-06-29

## 1. Tóm tắt một dòng

Android chụp ảnh giấy tờ → gửi sang OCR service chạy trên Windows (offline) →
nhận về JSON đã bóc tách, đạt tốc độ < 500 ms/ảnh.

## 2. Định hướng đã chốt (xem chi tiết tại DOC-04)

| Hạng mục | Lựa chọn |
|---|---|
| Nền tảng triển khai | Windows (OCR service), Android (chỉ chụp + hiển thị) |
| Ngôn ngữ/stack service | Python + FastAPI, đóng gói Windows Service |
| Runtime model | **CPU-first** (OpenVINO / ONNX Runtime), không dùng GPU |
| OCR engine | PaddleOCR (text detection) + VietOCR (recognition tiếng Việt) |
| Chiến lược đọc | Structured-data-first: QR / MRZ / barcode trước → OCR ROI bù trường thiếu |
| Bóc tách | Theo ROI template trên ảnh đã nắn phẳng (không OCR cả trang) |
| Mở rộng | Plugin theo từng loại giấy tờ (manifest YAML), core không sửa |
| Output | JSON thống nhất, có confidence từng trường |
| Chế độ mạng | Offline hoàn toàn |

## 3. Phần cứng tham chiếu

- CPU: Intel Core i7-14700 (20 nhân / 28 luồng) — **bộ xử lý chính cho inference**
- RAM: 16 GB
- GPU rời: AMD Radeon RX 6300 2 GB GDDR6 — **không dùng cho ML** (yếu, 2 GB VRAM, không CUDA)
- iGPU: Intel UHD Graphics 770 — có thể tăng tốc qua OpenVINO nếu cần

## 4. Bản đồ tài liệu

| Mã | Tài liệu | Trạng thái | Phụ thuộc |
|---|---|---|---|
| DOC-00 | [Tổng quan & Phạm vi](00-tong-quan-va-pham-vi.md) | DRAFT | — |
| DOC-01 | [Thuật ngữ & Danh mục giấy tờ](01-thuat-ngu-va-danh-muc-giay-to.md) | DRAFT | DOC-00 |
| DOC-02 | [Yêu cầu hệ thống](02-yeu-cau-he-thong.md) | DRAFT | DOC-00, DOC-01 |
| DOC-03 | [Kiến trúc tổng thể](03-kien-truc-tong-the.md) | DRAFT | DOC-02 |
| DOC-04 | [Quyết định công nghệ (ADR)](04-quyet-dinh-cong-nghe-adr.md) | DRAFT | DOC-03 |
| DOC-05 | [Phân loại & Thiết kế plugin](05-phan-loai-va-plugin.md) | DRAFT | DOC-03, DOC-04 |
| DOC-06 | [Pipeline OCR & Bóc tách](06-pipeline-ocr-va-boc-tach.md) | DRAFT | DOC-04, DOC-05 |
| DOC-07 | [Đặc tả API](07-dac-ta-api.md) | DRAFT | DOC-03 |
| DOC-08 | [Đặc tả trường & Validation](08-dac-ta-truong-va-validation.md) | DRAFT | DOC-01, DOC-05 |
| DOC-09 | [Android Capture SDK](09-android-capture-sdk.md) | DRAFT | DOC-07 |
| DOC-10 | [Triển khai & Hiệu năng](10-trien-khai-va-hieu-nang.md) | DRAFT | DOC-03, DOC-06 |

## 4b. Mẫu tham chiếu (hiệu chỉnh, không train)

Ảnh giấy tờ thật dùng để **hiệu chỉnh** nhãn/regex/ROI (theo ADR-012, không train):

| Mẫu | Loại | Trạng thái |
|---|---|---|
| [bhyt-mau-01](samples/bhyt-mau-01.md) | Thẻ BHYT | mã số 10 số (xác nhận), có QR |
| [the-dang-vien-mau-01](samples/the-dang-vien-mau-01.md) | Thẻ Đảng viên | label-anchored, nhãn không dấu `:` |
| [ho-chieu-mau-01](samples/ho-chieu-mau-01.md) | Hộ chiếu VN (cũ) | MRZ TD3, "Họ và tên" gộp, GCMND 9 số |
| [ho-chieu-mau-02](samples/ho-chieu-mau-02.md) | Hộ chiếu VN (mới) | tách Họ/Tên, ĐDCN 12 số, số HC 9 ký tự |
| [cmnd-9-mau-01](samples/cmnd-9-mau-01.md) | CMND 9 số | số in đỏ đè dấu, đường gạch chấm |
| [cccd-ma-vach-mau-01](samples/cccd-ma-vach-mau-01.md) | CCCD mã vạch | 12 số, mã tỉnh cross-check, thuần OCR |
| [cccd-chip-mau-01](samples/cccd-chip-mau-01.md) | CCCD gắn chip | QR mặt trước, chốt parser `cccd_qr` 7 trường |
| [gplx-pet-mau-01](samples/gplx-pet-mau-01.md) | GPLX PET (×3) | hạng/Class enum, ngày cấp dạng câu |
| [cccd-2024-mau-01](samples/cccd-2024-mau-01.md) | Căn cước 2024 (2 mặt) | QR+MRZ TD1 mặt sau, mỗi mặt 1 DOC-TYPE |

## 5. Thứ tự đọc đề xuất

Người mới: DOC-00 → DOC-01 → DOC-02 → DOC-03 → DOC-04 rồi tới các tài liệu kỹ thuật con.

## 6. Quy ước tài liệu

- Tên nghiệp vụ và tên giấy tờ: **tiếng Việt**. Tên kỹ thuật: **tiếng Anh**.
- Mã định danh: `FR-xxx` (functional), `NFR-xxx` (non-functional), `DEC-xxx`
  (decision), `ADR-xxx` (architecture decision record), `API-xxx`, `PLG-xxx` (plugin),
  `DOC-TYPE-xxx` (loại giấy tờ), `TST-xxx` (test).
- Mỗi quyết định công nghệ phải có một ADR truy vết được.
- Nguồn chân lý cho thuật ngữ: DOC-01.
