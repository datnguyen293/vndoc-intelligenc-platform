# rectifier

Nắn chỉnh ảnh chụp bị **nghiêng, méo, xoay góc** về dạng **chữ nhật/hình vuông thẳng hàng**.

- **Offline hoàn toàn** — pipeline thuần OpenCV, không cần Internet, không cần model
  (backend `classic` là mặc định). Backend YOLO chỉ là tùy chọn và dùng weights cục bộ.
- **Module để nhúng** vào project Python khác (`import rectifier`), kèm CLI tiện dụng.
- **Tổng quát + preset**: mặc định nắn mọi ảnh tài liệu; có preset tinh chỉnh sẵn cho
  thẻ ID, trang A4, hóa đơn, ảnh.

## Pipeline

```
Image → Segmentation → Largest Mask → 4 góc → Corner refine (sub-pixel)
      → Perspective warp → Auto-rotate → Deskew → Padding → CLAHE → Sharpen → Output
```

Có cơ chế **"nắn-khi-cần"**: ảnh vốn đã phẳng và lấp gần kín khung sẽ được giữ nguyên
(chỉ resize-cap), tránh xê dịch ảnh đã tốt.

## Cài đặt

```bash
pip install -e .            # lõi (opencv-python-headless, numpy, pillow)
pip install -e ".[yolo]"    # + backend YOLO tùy chọn (ultralytics)
pip install -e ".[dev]"     # + pytest
```

## Dùng như thư viện

```python
from PIL import Image
from rectifier import Rectifier, preset

r = Rectifier(preset("general"))          # general | id_card | document | receipt | photo
result = r.rectify(Image.open("in.jpg"))

result.image.save("out.jpg")              # ảnh PIL đã nắn
print(result.found)                       # True nếu tìm thấy & nắn, False nếu giữ nguyên
print(result.corners)                     # 4 góc trên ảnh gốc (TL, TR, BR, BL)
print(result.timings)                     # thời gian từng stage (ms)
```

Tiện cho một file:

```python
from rectifier import rectify_image
rectify_image("in.jpg", "out.jpg", preset="document")
```

Tinh chỉnh thêm khi lấy preset:

```python
cfg = preset("id_card", out_long=2400, denoise=True)
```

## Dùng như CLI

```bash
# một ảnh
python -m rectifier in.jpg out.jpg --preset general
rectifier in.jpg out.jpg                       # sau khi pip install (entry point)

# cả thư mục (giữ nguyên cấu trúc con với --recursive)
rectifier ./anh_vao ./anh_ra --preset document --recursive
```

## Preset

| Preset     | Ràng buộc tỉ lệ | Dùng cho                                  |
|------------|-----------------|-------------------------------------------|
| `general`  | không           | Mặc định — mọi ảnh tài liệu chụp nghiêng   |
| `id_card`  | 1.2–2.3, xoay ngang | CCCD/CMND/GPLX/BHYT (thẻ ID-1)        |
| `document` | 1.2–1.6         | Trang A4/Letter dọc                       |
| `receipt`  | không           | Hóa đơn/bill dài hẹp                       |
| `photo`    | không           | Ảnh — giữ màu, không tăng tương phản       |

Xem toàn bộ tham số trong [`rectifier/config.py`](rectifier/config.py) (`RectifyConfig`).

## Backend segmentation

- `classic` (mặc định): OpenCV thuần — Otsu + Canny + morphology. Nhanh (~20–120 ms),
  offline, không cần model.
- `yolo` (tùy chọn): YOLO segmentation qua `ultralytics`. Cần file weights `.pt` cục bộ:
  ```python
  Rectifier(preset("general", segmenter="yolo", yolo_weights="/duong/dan/doc-seg.pt"))
  ```
  Nếu thiếu weights hoặc lỗi nạp → tự fallback về `classic`.

## Test

```bash
pytest -q        # sinh ảnh tổng hợp nghiêng rồi kiểm chứng nắn lại, không cần ảnh ngoài
```
