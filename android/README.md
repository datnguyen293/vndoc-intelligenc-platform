# VNDoc Android SDK

Thư viện Android (AAR) + app mẫu để **chụp giấy tờ → gọi OCR service (LAN) → hiển thị + sửa
tay**. Thiết kế: [`docs/09-android-capture-sdk.md`](../docs/09-android-capture-sdk.md).

## Yêu cầu build
- Android Studio (Koala+), JDK 17, Android SDK (compileSdk 34), minSdk **30 (Android 11+)**.
- Mở thư mục `android/` bằng Android Studio (Gradle KTS + version catalog `gradle/libs.versions.toml`).

## Module
- **`vndoc-sdk`** — thư viện công khai: `VNDoc` (configure), `VNDocScanContract` (quét), CameraX
  + quality gate, review/sửa tay, OkHttp client.
- **`sample-app`** — demo: nhập cấu hình + quét theo từng loại giấy tờ.

## Tích hợp (host app)
```kotlin
// 1) Cấu hình 1 lần (màn Settings)
VNDoc.configure(context, ServerConfig(host = "192.168.1.50", port = 11001, apiKey = "…"))

// 2) Quét
val scan = registerForActivityResult(VNDocScanContract()) { result ->
    when (result) {
        is ScanResult.Success -> result.fields["idNumber"]?.value
        is ScanResult.Retry   -> /* nhắc chụp lại */
        is ScanResult.Error   -> /* 401/403/429/mạng */
        ScanResult.Cancelled  -> Unit
    }
}
scan.launch(DocType.CCCD)
```

## Lưu ý
- **HTTP cleartext** (LAN nội bộ): host app cần `network_security_config` cho phép cleartext
  (xem `sample-app/.../res/xml/network_security_config.xml`) + khai trong `<application>`.
- Quyền `CAMERA` do SDK khai; host app xin runtime (SDK tự xử lý ở màn chụp).
- Ảnh chỉ ở cache app, xoá sau xử lý; không lưu thư viện ảnh (NFR-007).

## Trạng thái
Khung V1 (scaffold). Cần build/tinh chỉnh trên Android Studio: ngưỡng quality gate thực địa,
cắt ảnh theo khung chính xác, luồng 2 mặt CCCD (app mẫu).
