# Thử nghiệm: detect 4 góc thẻ (nhánh `exp/rectifier-corner-detection`)

Áp dụng cơ chế các bài báo (4 góc → nắn phối cảnh) nhưng **hợp stack ta**: thay TF Object
Detection API bằng **YOLOv8-pose (torch/ONNX, CPU)**, và **tự sinh dữ liệu** (không có
dataset/weights tải được — mọi link trong bài đã chết).

⚠️ Nhánh THỬ NGHIỆM: tạm vượt ADR-012 ("không train") để đánh giá. Chưa merge vào `main`.

## Vì sao khác bài báo
| Bài báo | Ở đây | Lý do |
|---|---|---|
| TF Object Detection API | **YOLOv8-pose** (torch) | hợp stack (đã có torch), xuất ONNX chạy CPU, khớp hook `yolo` |
| 4 góc = 4 bbox → lấy tâm | 4 góc = **4 keypoint** | ra thẳng toạ độ góc, chính xác hơn "tâm box" |
| Data crawl + gán tay (link chết) | **Sinh tổng hợp** (homography + nền) | nhãn tự động, vô hạn, offline |

## Quy trình
```bash
PY=../../service/.venv/Scripts/python.exe

# 1) Sinh dữ liệu: thẻ phẳng + homography + nền nhiễu → ảnh + nhãn YOLO-pose (4 góc)
$PY synth.py --cards ../../service/samples --out data --n 6000

# 2) Train YOLOv8-pose-nano trên GPU (GTX 1070 Ti)
$PY train.py --data data/data.yaml --epochs 60 --imgsz 640

# 3) Xuất ONNX (chạy CPU offline khi tích hợp)
$PY export.py --weights runs/pose/train/weights/best.pt

# 4) Tích hợp: CornerDetector (ONNX) → 4 góc → order_points → warp (dùng lại geometry.py)
```

## Trạng thái
- [x] `synth.py` — sinh dữ liệu tổng hợp (verify: 4 góc bám khít mép thẻ).
- [ ] `train.py` — train YOLOv8-pose.
- [ ] `export.py` — ONNX.
- [ ] Tích hợp vào rectifier + so sánh vs classic trên ảnh thật.

## Giới hạn đã biết
- Nguồn chỉ ~38 ảnh thẻ (ít) → augmentation nặng bù lại; thêm ảnh thẻ phẳng sẽ tốt hơn.
- Xoay chỉ ±30° trong data (giữ keypoint ổn định); 90/180/270 để `OrientingOcr` lo.
