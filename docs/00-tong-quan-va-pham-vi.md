# DOC-00 — Tổng quan & Phạm vi

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** —

## 1. Bối cảnh & vấn đề

Tại đơn vị bộ đội, khi công dân/khách tới làm việc, cán bộ tiếp nhận phải ghi lại
thông tin nhân thân từ giấy tờ tuỳ thân vào sổ/biểu mẫu đăng ký. Việc gõ tay từng
trường vừa chậm, vừa dễ sai (đặc biệt số định danh, ngày tháng, địa chỉ có dấu).

Hệ thống này tự động bóc tách thông tin từ **bề mặt giấy tờ** ra JSON có cấu trúc,
giúp đăng ký khách nhanh và chính xác hơn.

## 2. Mục tiêu sản phẩm

1. Chụp ảnh giấy tờ bằng thiết bị Android, bóc tách thông tin trên máy Windows.
2. Trả về JSON thống nhất, có độ tin cậy (confidence) cho từng trường.
3. Đạt tốc độ xử lý **< 500 ms/ảnh** trên phần cứng tham chiếu.
4. Chạy **offline hoàn toàn** (không gửi dữ liệu ra Internet — yêu cầu an ninh).
5. Mở rộng được sang loại giấy tờ mới mà không sửa lõi hệ thống.

## 3. Người dùng

- Cán bộ trực ban / bảo vệ cổng
- Cán bộ tiếp nhận, hành chính
- Ứng dụng nghiệp vụ tích hợp qua API (đăng ký khách, sổ trực)

## 4. Kịch bản sử dụng chính

1. Cán bộ mở app Android, chọn chụp giấy tờ.
2. App hiển thị khung căn, hướng dẫn đặt giấy tờ vừa khung, đủ sáng, không loá.
3. App kiểm tra nhanh chất lượng ảnh phía client; nếu mờ/nghiêng thì nhắc chụp lại.
4. Ảnh đạt yêu cầu được gửi sang OCR service (Windows) qua REST API trong mạng nội bộ.
5. Service phát hiện giấy tờ, nhận dạng loại, đọc QR/MRZ/barcode nếu có, OCR các
   trường còn lại, kiểm tra hợp lệ, chuẩn hóa và trả JSON.
6. App hiển thị kết quả để cán bộ rà soát, chỉnh tay nếu cần, rồi lưu vào nghiệp vụ.

## 5. Phạm vi phiên bản 1.0

### 5.1 Trong phạm vi

- Tiếp nhận ảnh từ Android (JPEG/PNG).
- Đánh giá chất lượng ảnh (mờ, sáng, tương phản, nghiêng, méo phối cảnh).
- Phát hiện vùng giấy tờ và nắn phối cảnh về mặt phẳng chuẩn.
- Nhận dạng loại giấy tờ (hoặc trả `unknown`).
- Chỉ xử lý **mặt trước** của giấy tờ 2 mặt (CCCD). Mặt sau ngoài phạm vi.
- Đọc dữ liệu máy đọc: **QR code, MRZ, barcode** khi giấy tờ có (mặt trước).
- OCR theo vùng (ROI) cho các trường text.
- Kiểm tra hợp lệ, chuẩn hóa dữ liệu, tính confidence.
- Trả JSON thống nhất; tuỳ chọn trả ảnh đã cắt/đánh dấu.
- Ghi log và đo thời gian xử lý.
- Cơ chế plugin để thêm loại giấy tờ.

### 5.2 Ngoài phạm vi (V1)

- Nhận diện khuôn mặt, đối chiếu chân dung.
- Đọc chip NFC (kể cả CCCD gắn chip — chỉ đọc **bề mặt**, không đọc chip).
- Liveness / chống giả mạo giấy tờ.
- OCR chữ viết tay.
- Cloud OCR / đồng bộ dữ liệu lên cloud.
- Công cụ gán nhãn, quản lý tập train, cổng web quản trị.
- **Mặt sau của CCCD** (gắn chip và mã vạch): không xử lý ở V1 — mặt trước đã đủ
  trường nhân thân cần cho đăng ký khách.

> Ghi chú 1: CCCD gắn chip vẫn được hỗ trợ ở V1, bóc tách từ **mặt trước** (gồm
> **mã QR ở góc trên phải mặt trước**), **không** đọc chip qua NFC.
>
> Ghi chú 2: CCCD mã vạch (đời cũ) có barcode ở mặt sau; vì chỉ xử lý mặt trước nên
> loại này được bóc tách thuần bằng OCR.

## 6. Loại giấy tờ hỗ trợ V1 (10 loại)

Xem danh mục chuẩn có mã tại [DOC-01](01-thuat-ngu-va-danh-muc-giay-to.md).

1. CCCD gắn chip — Mặt trước (có QR ở mặt trước)
2. CCCD mã vạch — Mặt trước
3. CMND 09 số
4. Hộ chiếu Việt Nam (trang nhân thân, có MRZ)
5. GPLX PET (giấy phép lái xe vật liệu PET)
6. Thẻ BHYT
7. **Thẻ Đảng viên**
8. **Thẻ quân nhân**
9. Căn cước 2024 — Mặt trước (thẻ "CĂN CƯỚC" từ 01/07/2024)
10. Căn cước 2024 — Mặt sau (có QR + MRZ TD1 + địa chỉ)

> Ghi chú 1: CMND 12 số đã được loại khỏi phạm vi (gần như không tồn tại thực tế).
>
> Ghi chú 2: Thẻ Căn cước 2024 nhận **1 ảnh — mặt trước HOẶC mặt sau** (mỗi mặt phân
> loại và bóc tách độc lập). Mặt sau tự chứa MRZ + QR + địa chỉ nên thường đủ một mình.

> Thẻ Đảng viên và Thẻ quân nhân là giấy tờ nội bộ, **không có template công khai**.
> Cần đơn vị cung cấp ảnh mẫu thật để dựng ROI map. Hai loại này được thiết kế ở dạng
> "khung plugin chờ mẫu" và ráp hoàn chỉnh khi có dữ liệu. Đây cũng là loại dữ liệu
> nhạy cảm về an ninh — xem ràng buộc bảo mật ở DOC-02 (NFR) và DOC-10.

## 7. Tiêu chí thành công

- Ảnh đạt chất lượng được nhận dạng đúng loại trong phần lớn trường hợp.
- Với CCCD gắn chip có QR rõ → bóc tách trường nhân thân gần như tuyệt đối nhờ QR.
- JSON trả về có cấu trúc nhất quán và có confidence.
- Thời gian xử lý trung bình < 500 ms/ảnh trên phần cứng tham chiếu.
- Thêm loại giấy tờ mới bằng plugin, không sửa core.

## 8. Quyết định đã khóa

| ID | Quyết định |
|---|---|
| DEC-001 | Windows là nền tảng chạy OCR service |
| DEC-002 | Android chỉ capture, hiển thị; không OCR trên thiết bị |
| DEC-003 | Hệ thống hoạt động offline hoàn toàn |
| DEC-004 | Output luôn là JSON thống nhất, có confidence |
| DEC-005 | V1 hỗ trợ 10 loại giấy tờ (gồm Thẻ Đảng viên, Thẻ quân nhân, Căn cước 2024 trước/sau); bỏ CMND 12 số |
| DEC-006 | Chỉ bóc tách bề mặt giấy tờ; không đọc chip NFC ở V1 |
| DEC-007 | Thêm loại giấy tờ mới bằng plugin, không sửa core engine |
| DEC-008 | CCCD/CMND đời cũ (trước 01/07/2024): chỉ xử lý mặt trước. Thẻ Căn cước 2024: nhận 1 ảnh mặt trước HOẶC mặt sau (độc lập) |
| DEC-009 | Pipeline phải tự chuẩn hóa hướng ảnh (0/90/180/270°) trước OCR (xem DOC-06 S3) |
