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

## Bước B — fine-tune bằng ẢNH THẬT gán nhãn (thu hẹp nốt gap)

Iter 1 (synth v1) fail trên ảnh thật; iter 2 (synth v2: nền thật+bao nhựa) đã tổng quát khá
(bám được thẻ trong bao trên bàn gỗ) nhưng chưa khít mép in. Bước B: gán vài chục ảnh thật.

```bash
PY=../../service/.venv/Scripts/python.exe

# 1) Bỏ ảnh thẻ THẬT (đa dạng nền/nghiêng/bao) vào  real_images/
# 2) Gán 4 góc bằng GUI (bấm 4 góc/ảnh; tự bỏ qua ảnh đã gán → gán theo đợt)
$PY label_corners.py --images real_images --out real_data

# 3) Fine-tune từ best.pt trên SYNTH + REAL gộp (LR thấp, tránh overfit ít ảnh thật)
$PY finetune.py --weights runs/pose/weights/best.pt --synth data --real real_data

# 4) Đánh giá lại bằng anchor
DIP_OCR_BACKEND=vietocr DIP_OCR_DEVICE=cpu $PY evaluate.py \
    --weights runs/finetune/weights/best.pt --images real_images/<ảnh>:<hint> ...
```

## Trạng thái
- [x] `synth.py` v2 — nền thật + bao nhựa + domain randomization.
- [x] `train.py` — train YOLOv8-pose (val mAP tốt; v2 tổng quát khá sang ảnh thật).
- [x] `corner_rectify.py` + `evaluate.py` — inference + so sánh anchor.
- [x] `label_corners.py` + `finetune.py` — công cụ gán 4 góc + fine-tune (bước B).
- [ ] Fine-tune trên ảnh thật đủ tốt → export ONNX → tích hợp rectifier (fallback khi classic fail).

## Giới hạn / bài học
- Val synth cao (0.99) KHÔNG đồng nghĩa tốt trên thật (iter 1 chứng minh) → phải đánh giá ảnh thật.
- Trên thẻ LẤP KHUNG, classic vốn đã tốt → corner ngang bằng; corner THẮNG ở ca thẻ NHỎ/nền nhiễu.
  → nên dùng corner làm **fallback/bổ trợ** khi classic không ra tứ giác tốt, không thay thế mù.
- Nguồn synth chỉ ~38 ảnh thẻ; bước B (ảnh thật) là đòn bẩy tổng quát mạnh nhất.
