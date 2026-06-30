# DOC-09 — Android Capture SDK

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-07
- **Truy vết:** FR-001, FR-002 (phần client), NFR-007

## 1. Vai trò của Android

Android **chỉ** làm 3 việc: chụp ảnh chất lượng tốt, gửi sang OCR service, hiển thị
kết quả cho cán bộ rà soát/sửa tay. **Không** chạy OCR trên thiết bị (DEC-002).

## 2. Phạm vi SDK

- Màn hình camera có **khung căn (overlay)** theo tỉ lệ giấy tờ.
- **Quality gate phía client** (sơ bộ) để giảm ảnh hỏng gửi lên server.
- Đóng gói & gửi ảnh qua `multipart/form-data` tới API-001.
- Nhận JSON, map sang model hiển thị, cho phép sửa và lưu vào nghiệp vụ.

## 3. Luồng màn hình

```text
[Chọn loại GT (tuỳ chọn)] → [Camera + khung căn] → [Tự kiểm tra chất lượng]
   → đạt → [Chụp/Tự chụp] → [Gửi API] → [Hiển thị kết quả + sửa] → [Lưu]
   → kém → [Nhắc: dịch lại/đủ sáng/giữ yên] (không cho chụp)
```

## 4. Hướng dẫn chụp (UX)

- Overlay khung theo tỉ lệ thẻ ID-1 (~1.585:1) hoặc hộ chiếu; yêu cầu giấy tờ **lấp
  đầy khung**, song song mép.
- Hiển thị gợi ý thời gian thực: "Đưa lại gần", "Giữ máy yên", "Tránh loá", "Đủ sáng".
- Ưu tiên **chụp tự động** khi khung ổn định + nét (giảm rung do bấm nút).
- Tắt làm đẹp/làm mịn; giữ ảnh gốc sắc nét.

## 5. Quality gate phía client (sơ bộ)

Mục tiêu giảm round-trip ảnh hỏng (server vẫn kiểm lại ở FR-002):

| Chỉ số | Cách đo trên Android | Ngưỡng (khởi điểm) |
|---|---|---|
| Độ nét | variance Laplacian (qua OpenCV Android / RenderScript thay thế) | > ngưỡng blur |
| Độ sáng | trung bình luminance | trong [60, 200] |
| Loá | tỉ lệ pixel bão hòa | < 5% |
| Lấp khung | tỉ lệ diện tích thẻ/khung | > 80% |
| Ổn định | gia tốc kế / độ lệch khung giữa frame | thấp |

Không đạt → chưa cho chụp, hiện gợi ý. Đạt → cho chụp/tự chụp.

## 6. Thông số ảnh gửi lên

| Tham số | Khuyến nghị |
|---|---|
| Định dạng | JPEG (chất lượng ~90) |
| Cạnh dài | 1600–2000 px (đủ nét chữ nhỏ, không quá nặng) |
| Kích thước | mục tiêu < 2–3 MB (giới hạn server 8 MB) |
| Màu | giữ màu, không grayscale |
| Metadata | gỡ EXIF vị trí (riêng tư), giữ orientation đã xoay đúng |

## 7. Gọi API (ví dụ)

```text
POST /api/v1/extract  (multipart/form-data)
parts:
  image:        <file jpeg>
  docTypeHint:  cccd_chip_front     # nếu người dùng đã chọn loại
  returnImage:  none
headers:
  X-API-Key: <khóa nội bộ>          # nếu service bật
```

Xử lý phản hồi:
- `documentType=unknown` hoặc `overallConfidence` thấp → gợi ý chụp lại.
- Trường có `confidence` thấp → tô màu cảnh báo, nhắc cán bộ kiểm tra.
- Cho phép **sửa tay** mọi trường trước khi lưu (OCR là hỗ trợ, không thay người).

## 8. Cấu hình & kết nối

- Cấu hình được **địa chỉ server nội bộ** (IP:port) và API key.
- Hoạt động trong **mạng LAN/Wi-Fi nội bộ**, không cần Internet.
- Khuyến nghị HTTPS nội bộ (chứng chỉ tự ký cài sẵn) cho dữ liệu nhạy cảm (NFR-007).
- Timeout hợp lý (vd 5 s) + thử lại 1 lần; báo lỗi rõ khi mất kết nối.

## 9. Riêng tư trên thiết bị (NFR-007)

- Không lưu ảnh giấy tờ vào thư viện ảnh công khai; dùng bộ nhớ tạm app.
- Xóa ảnh tạm sau khi xử lý xong / theo cấu hình.
- Không gửi dữ liệu đi bất kỳ đâu ngoài server nội bộ.

## 10. Khuyến nghị kỹ thuật (không bắt buộc)

- CameraX cho preview + phân tích frame realtime.
- Thư viện xử lý ảnh nhẹ để đo nét/sáng (OpenCV Android hoặc tự cài Laplacian).
- Module mạng (Retrofit/OkHttp) cho multipart.

## 11. Quyết định khóa
| ID | Quyết định |
|---|---|
| DEC-060 | Android chỉ capture/hiển thị, có quality gate sơ bộ phía client |
| DEC-061 | Ảnh gửi JPEG ~90, cạnh dài 1600–2000 px |
| DEC-062 | OCR là hỗ trợ; cán bộ luôn được sửa tay trước khi lưu |
| DEC-063 | Không lưu ảnh ra nơi công khai; xóa ảnh tạm sau xử lý |
