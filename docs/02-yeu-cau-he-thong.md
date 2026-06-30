# DOC-02 — Yêu cầu hệ thống

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-00, DOC-01

Mọi tài liệu thiết kế, API, test phải truy vết về requirement trong tài liệu này.

## 1. Functional Requirements (FR)

### FR-001 — Tiếp nhận ảnh
Hệ thống phải nhận ảnh do Android gửi lên, định dạng JPEG hoặc PNG, qua REST API.

### FR-002 — Kiểm tra chất lượng ảnh
Hệ thống phải đánh giá tối thiểu: độ mờ (blur), độ sáng, độ tương phản, độ nghiêng,
méo phối cảnh. Nếu ảnh quá kém, trả cảnh báo để client chụp lại.

### FR-003 — Phát hiện giấy tờ
Hệ thống phải xác định vùng chứa giấy tờ (bounding box / polygon) trong ảnh.

### FR-004 — Hiệu chỉnh phối cảnh
Hệ thống phải cắt và nắn ảnh giấy tờ về template chuẩn để OCR ổn định.

### FR-005 — Nhận dạng loại giấy tờ
Hệ thống phải xác định một trong các loại ở DOC-01, hoặc trả `unknown`.

### FR-006 — Đọc dữ liệu máy đọc
Khi giấy tờ có QR / MRZ / barcode, hệ thống phải **ưu tiên đọc các vùng này trước**
và dùng kết quả làm nguồn chính cho các trường tương ứng (structured-data-first).

### FR-007 — Nạp plugin theo loại giấy tờ
Hệ thống phải nạp đúng plugin tương ứng với loại giấy tờ đã nhận dạng.

### FR-008 — Trích xuất trường dữ liệu
Hệ thống phải bóc tách các trường khai báo trong plugin, theo ROI và/hoặc từ dữ
liệu máy đọc.

### FR-009 — OCR theo vùng
Với các trường không có sẵn từ dữ liệu máy đọc, hệ thống phải OCR theo ROI.

### FR-010 — Kiểm tra hợp lệ
Hệ thống phải kiểm tra theo regex, độ dài, định dạng ngày tháng, checksum (MRZ,
mã BHYT...) và quy tắc nghiệp vụ cấu hình trong plugin.

### FR-011 — Chuẩn hóa dữ liệu
Hệ thống phải chuẩn hóa: ngày tháng về ISO, giới tính, số định danh, viết hoa/thường,
tiếng Việt có dấu khi phù hợp.

### FR-012 — Đối chiếu chéo (cross-check)
Khi cùng một trường đến từ nhiều nguồn (QR vs OCR, hai mặt giấy tờ), hệ thống phải
đối chiếu và nâng/hạ confidence, ghi cảnh báo khi lệch.

### FR-013 — Tính confidence
Hệ thống phải trả confidence cho từng trường và confidence tổng.

### FR-014 — Trả JSON
Hệ thống phải trả JSON thống nhất gồm tối thiểu: `requestId`, `documentType`,
`processingTimeMs`, `fields`, `warnings`, `errors`.

### FR-015 — Tuỳ chọn trả ảnh xử lý
Theo yêu cầu client, hệ thống có thể trả ảnh đã cắt/nắn/đánh dấu vùng đọc.

### FR-016 — Ghi log
Hệ thống phải ghi log: request, loại giấy tờ, thời gian xử lý, warning, error.

### FR-017 — Hỗ trợ plugin
Hệ thống phải cho phép thêm loại giấy tờ mới bằng plugin, không sửa core engine.

### FR-018 — Cấu hình ngoài mã nguồn
Hệ thống phải đọc cấu hình và plugin từ thư mục riêng, ngoài core.

### FR-019 — Xử lý đồng thời
Hệ thống phải phục vụ nhiều request đồng thời mà vẫn giữ mục tiêu hiệu năng.

### FR-020 — Chế độ offline
Hệ thống phải hoạt động đầy đủ khi không có Internet.

## 2. Non-functional Requirements (NFR)

### NFR-001 — Hiệu năng
Thời gian xử lý trung bình một ảnh đạt chất lượng < **500 ms** trên phần cứng tham
chiếu (i7-14700, 16 GB RAM, **CPU-only**). P95 mục tiêu < 800 ms.

### NFR-002 — Khả dụng
Chạy ổn định như một Windows Service / tiến trình nền, tự khởi động lại khi lỗi.

### NFR-003 — Khả mở rộng
Core engine không phụ thuộc cứng vào từng loại giấy tờ; thêm loại = thêm plugin.

### NFR-004 — Khả bảo trì
Thay đổi một plugin không ảnh hưởng plugin khác hay core.

### NFR-005 — Nhất quán
JSON output nhất quán giữa các loại giấy tờ (cùng schema, khác tập field).

### NFR-006 — Truy vết
Mọi module, API, test phải truy vết về requirement tương ứng.

### NFR-007 — Bảo mật & quyền riêng tư
- Hệ thống xử lý dữ liệu cá nhân và giấy tờ nhạy cảm (gồm Thẻ Đảng viên, quân nhân).
- **Không** gửi bất kỳ dữ liệu nào ra ngoài mạng nội bộ.
- Không lưu ảnh gốc lâu hơn mức cần thiết để xử lý; mặc định không lưu ảnh ra đĩa,
  chỉ giữ trong bộ nhớ tiến trình (cấu hình được).
- Log không chứa toàn văn dữ liệu nhân thân (mask số định danh trong log).
- Giao tiếp Android ↔ service nên qua HTTPS nội bộ và/hoặc token chia sẻ.

### NFR-008 — Tài nguyên
Tiêu thụ RAM tiến trình mục tiêu < 4 GB khi tải warm model; không phụ thuộc GPU.

### NFR-009 — Khả kiểm thử
Pipeline phải cho phép test từng stage độc lập với bộ ảnh mẫu cố định.

## 3. Giả định

- Mỗi request chứa một ảnh chính, xử lý một mặt giấy tờ.
- Ảnh do Android gửi đã được nén hợp lý và đã qua quality gate phía client.
- Người vận hành có thể chụp lại nếu chất lượng thấp.
- Với giấy tờ 2 mặt (CCCD), client có thể gửi 2 request riêng cho 2 mặt; ghép ở
  tầng nghiệp vụ (hoặc theo cơ chế phiên — bàn ở DOC-07).

## 4. Ràng buộc

- Windows là nền tảng chạy service; Android chỉ capture + hiển thị.
- CPU-only (không dùng GPU rời AMD RX 6300).
- JSON là output chuẩn duy nhất.
- Offline là bắt buộc.

## 5. Traceability (sơ bộ)

| Requirement | Thiết kế liên quan |
|---|---|
| FR-002, FR-003, FR-004 | DOC-06 |
| FR-005, FR-007 | DOC-05 |
| FR-006, FR-008, FR-009 | DOC-06 |
| FR-010, FR-011, FR-012 | DOC-08 |
| FR-014, FR-015 | DOC-07 |
| FR-019 | DOC-10 |
| NFR-001, NFR-008 | DOC-04, DOC-10 |
| NFR-007 | DOC-10 |

## 6. Quyết định đã khóa

| ID | Quyết định |
|---|---|
| DEC-010 | Requirement phải có mã ID và được truy vết |
| DEC-011 | Mục tiêu hiệu năng đo trên CPU-only, không tính tới GPU |
| DEC-012 | Structured-data (QR/MRZ/barcode) là nguồn ưu tiên hơn OCR |
| DEC-013 | Không lưu ảnh gốc ra đĩa theo mặc định (NFR-007) |
