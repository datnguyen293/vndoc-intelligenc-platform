# HƯỚNG DẪN CÀI ĐẶT & CẤU HÌNH — VNDoc OCR Service

**Dành cho cán bộ triển khai.** Tài liệu hướng dẫn cài phần mềm đọc giấy tờ tuỳ thân lên
máy tính Windows và cấu hình để điện thoại Android trong cùng mạng chụp gửi được.

> Toàn bộ chạy **offline** (không cần Internet sau khi cài). Ảnh xử lý trong bộ nhớ, **không
> lưu ra đĩa**.

---

## 1. Chuẩn bị

| Hạng mục | Yêu cầu |
|---|---|
| Hệ điều hành | Windows 10 / 11 **64-bit** |
| RAM | Tối thiểu 4 GB (khuyến nghị 8 GB) |
| Ổ đĩa trống | ≥ 3 GB |
| Quyền | **Administrator** (để cài dịch vụ) |
| Mạng | Máy tính và điện thoại Android **CÙNG một mạng LAN** (chung Wi-Fi/switch nội bộ) |
| Tệp cài | `VNDoc-Setup-0.1.0.exe` (bộ cài đã được cung cấp) |

---

## 2. Cài đặt (khoảng 5 phút)

1. Chép `VNDoc-Setup-0.1.0.exe` vào máy tính sẽ chạy dịch vụ.
2. **Chuột phải** vào tệp → **Run as administrator** (hoặc nháy đúp, bấm **Yes** ở hộp thoại
   xin quyền).
3. Chọn thư mục cài (để mặc định `C:\Program Files\VNDoc`) → **Next** → **Install**.
4. Chờ giải nén (~1–2 phút). Bộ cài **tự động**:
   - Tạo cấu hình và **sinh sẵn một API Key ngẫu nhiên**.
   - Đăng ký dịch vụ Windows tên **VNDoc OCR Service** (tự chạy cùng máy, tự khởi động lại
     nếu lỗi).
   - Mở tường lửa cổng **11001** cho mạng nội bộ.
   - Khởi động dịch vụ.
5. Bấm **Finish**. Xong — dịch vụ đã chạy nền ở cổng **11001**.

> Lần chạy đầu tiên dịch vụ cần ~10–20 giây để nạp mô hình. Đây là điều bình thường.

---

## 3. Lấy API Key (bắt buộc để cấu hình Android)

1. Mở thư mục cài, vào `config`, mở tệp **`vndoc.env`** bằng **Notepad**
   (đường dẫn: `C:\Program Files\VNDoc\config\vndoc.env`).
2. Tìm dòng:
   ```
   DIP_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Chuỗi sau dấu `=` là **"chìa khoá"** để điện thoại được phép gọi dịch vụ.
   **Ghi lại / sao chép** chuỗi này để nhập vào app Android (mục 6).

> Muốn đổi sang key khác: sửa chuỗi này rồi **khởi động lại dịch vụ** (mục 5).

---

## 4. Cấu hình mạng LAN (QUAN TRỌNG)

Điện thoại chỉ gọi được nếu **địa chỉ IP của nó nằm trong dải cho phép**. Mặc định cho phép
`127.0.0.1/32` (chính máy) và `192.168.0.0/24`.

**Kiểm tra dải mạng của đơn vị:**
1. Trên máy tính, bấm **Start**, gõ `cmd`, mở **Command Prompt**.
2. Gõ `ipconfig` rồi Enter. Tìm dòng **IPv4 Address**, ví dụ `192.168.1.50`.
3. Đối chiếu:
   - Nếu IP máy dạng `192.168.0.x` → **giữ nguyên**, không cần sửa.
   - Nếu khác (vd `192.168.1.x`, `10.0.0.x`) → mở `config\vndoc.env`, sửa dòng
     `DIP_ALLOWED_IPS` cho khớp. Ví dụ mạng `192.168.1.x`:
     ```
     DIP_ALLOWED_IPS=127.0.0.1/32,192.168.1.0/24
     ```
4. Lưu tệp → **khởi động lại dịch vụ** (mục 5).

> **Ghi lại địa chỉ IPv4 của máy** (vd `192.168.1.50`) — sẽ nhập vào app Android ở mục 6.

> 🧪 **Môi trường TESTING — cho phép MỌI IP (không giới hạn):** đặt
> `DIP_ALLOWED_IPS=*` rồi khởi động lại dịch vụ. Mọi thiết bị trong mạng đều gọi được (khỏi
> cần khai đúng dải). **Chỉ dùng khi thử nghiệm**, môi trường thật nên khai đúng dải LAN.

---

## 5. Bật / tắt / khởi động lại dịch vụ

**Cách 1 — bằng cửa sổ Services (dễ):**
1. Bấm **Start**, gõ `services.msc`, mở **Services**.
2. Tìm **VNDoc OCR Service** → **chuột phải** → chọn **Start** / **Stop** / **Restart**.

**Cách 2 — bằng lệnh (Command Prompt chạy Administrator):**
```
sc stop VNDocOCR
sc start VNDocOCR
```

> **Mỗi lần sửa `vndoc.env` (API key, dải IP…) đều phải khởi động lại dịch vụ** thì thay đổi
> mới có hiệu lực.

---

## 6. Cấu hình app Android

Nhập vào app trên điện thoại (cùng mạng LAN với máy tính):

| Thông tin | Giá trị |
|---|---|
| Địa chỉ máy chủ | `http://<IP-máy>:11001` — ví dụ `http://192.168.1.50:11001` (IP lấy ở mục 4) |
| API Key | chuỗi `DIP_API_KEY` lấy ở mục 3 |
| Loại giấy tờ | Cán bộ **chọn loại giấy tờ trước khi chụp** (app gửi kèm mỗi lần chụp — bắt buộc) |

---

## 7. Kiểm tra hoạt động

**Tại máy chạy dịch vụ:** mở trình duyệt, vào:
```
http://127.0.0.1:11001/api/v1/health
```
Thấy `{"status":"ok", ...}` là dịch vụ đang chạy tốt.

**Từ điện thoại (cùng mạng):** mở trình duyệt điện thoại, vào
`http://<IP-máy>:11001/api/v1/health`. Nếu thấy `status: ok` → điện thoại đã thông tới máy.
Không vào được → xem **mục 8**.

---

## 8. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| Dịch vụ không chạy | Chưa khởi động / lỗi khởi động | `services.msc` → Start; xem log tại `C:\Program Files\VNDoc\logs` |
| Điện thoại **không kết nối được** (chờ mãi) | Khác dải IP hoặc tường lửa chặn | Sửa `DIP_ALLOWED_IPS` (mục 4); kiểm tra tường lửa (mục 9); đảm bảo chung mạng |
| Báo lỗi **401** (Unauthorized) | Sai/thiếu API Key trên app | Nhập đúng chuỗi `DIP_API_KEY` (mục 3) |
| Báo lỗi **403** (Forbidden) | IP điện thoại ngoài dải cho phép | Thêm dải IP vào `DIP_ALLOWED_IPS` (mục 4) rồi restart |
| Báo lỗi **400** (Thiếu docTypeHint) | App không gửi loại giấy tờ | Chọn loại giấy tờ trên app trước khi chụp |
| Lần đầu xử lý hơi chậm | Đang nạp mô hình | Bình thường; các lần sau nhanh hơn |

---

## 9. Mở tường lửa thủ công (nếu điện thoại vẫn không gọi được)

Bộ cài **đã tự mở** cổng 11001. Nếu vẫn bị chặn (do chính sách máy), mở **Command Prompt
(Administrator)** và chạy:
```
netsh advfirewall firewall add rule name="VNDoc OCR 11001" dir=in action=allow protocol=TCP localport=11001 profile=private,domain
```

---

## 10. Gỡ cài đặt

- **Settings → Apps → Installed apps** → tìm **VNDoc OCR Service** → **Uninstall**.
- Quá trình gỡ sẽ dừng & xoá dịch vụ và luật tường lửa. Thư mục `config` và `logs` **được
  giữ lại** (phòng khi cài lại dùng cấu hình cũ) — xoá tay nếu cần.

---

## 11. Lưu ý an toàn

- **Giữ bí mật API Key**; chỉ cấp cho thiết bị Android được phép.
- Chỉ mở dịch vụ cho **mạng nội bộ**; không để lộ ra Internet.
- Dịch vụ **không lưu ảnh** giấy tờ ra đĩa; số định danh được che bớt trong log.

---

*Cần hỗ trợ kỹ thuật sâu hơn (build lại bộ cài, cấu hình nâng cao): xem `packaging/README.md`
và `docs/11-dong-goi-cai-dat-va-cap-phep.md`.*
