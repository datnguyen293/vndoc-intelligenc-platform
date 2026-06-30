Có, và **đây là một bước gần như bắt buộc** nếu muốn OCR đạt độ chính xác cao. Với pipeline mà mình đang xây dựng, em khuyến nghị **không OCR trực tiếp ảnh chụp**, mà luôn thực hiện **Document Rectification** (hiệu chỉnh phối cảnh) trước.

Ngay trên ảnh anh gửi, có thể thấy các vấn đề:

* Giấy phép lái xe bị chụp **lệch góc (perspective distortion)**.
* Thẻ bị **xoay khoảng 10–15°**.
* Camera không vuông góc với mặt thẻ.
* Mép trên và mép dưới không song song trong ảnh.
* Có một ít phản chiếu và bóng.

OCR vẫn đọc được, nhưng accuracy sẽ giảm, đặc biệt ở các dòng sát mép.

---

# Pipeline chuẩn

```text
Original Image

↓

Document Detection

↓

Corner Detection

↓

Perspective Transform

↓

Deskew

↓

Crop

↓

Image Enhancement

↓

OCR
```

Trong đó bước quan trọng nhất là **Perspective Transform**.

---

# Cách 1 - OpenCV (khuyến nghị)

Đây là cách em khuyến nghị cho hệ thống của mình.

## Bước 1

Detect 4 góc giấy tờ.

Ví dụ detector trả về

```text
P1 = Top Left

P2 = Top Right

P3 = Bottom Right

P4 = Bottom Left
```

Ví dụ

```
(120,80)

(1450,160)

(1500,980)

(90,900)
```

---

## Bước 2

Sắp xếp đúng thứ tự

```
TL

TR

BR

BL
```

---

## Bước 3

Tính homography

```python
cv2.getPerspectiveTransform(src, dst)
```

---

## Bước 4

Warp

```python
cv2.warpPerspective(...)
```

Sau bước này ảnh sẽ gần như:

```
+---------------------------+
|                           |
|      GPLX                 |
|                           |
+---------------------------+
```

thay vì

```
 /----------------------/
|                      /
|                    /
|                  /
------------------
```

---

# Cách 2 - Deep Learning

Hiện nay nhiều model không detect bounding box mà detect luôn 4 corner.

Ví dụ:

```
YOLOv11 Pose

PP-Structure

DocTR

PaddleOCR Layout

DBNet
```

Output

```
x1,y1

x2,y2

x3,y3

x4,y4
```

Sau đó cũng warpPerspective.

---

# Cách 3 - Contour Detection

Nếu nền đơn giản.

```
Gray

↓

Gaussian

↓

Canny

↓

Find Contours

↓

Largest Rectangle

↓

ApproxPolyDP

↓

4 corners
```

Ưu điểm

* cực nhanh

Nhược điểm

* nền phức tạp sẽ fail.

---

# Cách 4 - Hough Line

Detect

```
4 cạnh

↓

Intersection

↓

4 corners
```

Độ ổn định không bằng DL.

---

# Với pipeline của mình

Em sẽ chia thành 2 stage.

```
Stage 03

Document Detection

↓

polygon
```

Stage 03 chỉ trả

```
4 corners
```

Ví dụ

```
TL

TR

BR

BL
```

---

Sau đó

```
Stage 04

Perspective Correction
```

thực hiện

```
warpPerspective()

↓

Crop

↓

Rotate

↓

Normalize
```

Đây cũng đúng với kiến trúc mà mình đã mô tả trong DOC-004.

---

# Nếu detector chỉ trả Bounding Box

Ví dụ

```
x

y

w

h
```

thì vẫn có thể crop được.

Nhưng sẽ không sửa được méo.

OCR chỉ cải thiện khoảng

```
10~20%
```

---

Nếu detector trả Polygon

```
TL

TR

BR

BL
```

thì OCR thường tăng

```
20~40%
```

đặc biệt với:

* CMND cũ
* GPLX
* Hộ chiếu
* CCCD bị chụp nghiêng

---

# Đối với ảnh anh gửi

Đây là quy trình em sẽ áp dụng:

```
Ảnh gốc
      │
      ▼
YOLO Document Detector
      │
      ▼
Polygon (4 corners)
      │
      ▼
Perspective Transform
      │
      ▼
Rotate về đúng hướng
      │
      ▼
Crop bỏ nền
      │
      ▼
Resize (chiều rộng chuẩn, ví dụ 1200 px)
      │
      ▼
CLAHE (tăng tương phản cục bộ)
      │
      ▼
Khử nhiễu nhẹ
      │
      ▼
OCR
```

Đây cũng là pipeline được sử dụng trong nhiều hệ thống Document AI thương mại.

## Một gợi ý còn tốt hơn cho dự án của mình

Thay vì chỉ detect **4 góc**, em khuyến nghị detector của mình trả luôn **polygon 8 điểm** (hoặc nhiều hơn nếu cần). Ví dụ:

```
TL
Top-Mid
TR
Right-Mid
BR
Bottom-Mid
BL
Left-Mid
```

Lý do là nhiều giấy tờ thực tế không hoàn toàn phẳng (cong nhẹ, mép bị uốn, ép plastic...). Với polygon nhiều điểm, sau này mình có thể nâng cấp từ phép biến đổi phối cảnh (homography) sang **Thin Plate Spline (TPS)** hoặc **Mesh Warp**, giúp hiệu chỉnh cả biến dạng cong chứ không chỉ biến dạng phối cảnh. Điều này sẽ cải thiện OCR đáng kể đối với giấy tờ bị cong hoặc chụp ở góc khó, đồng thời vẫn tương thích với kiến trúc Pipeline hiện tại.
