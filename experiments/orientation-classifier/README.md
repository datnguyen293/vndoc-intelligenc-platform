# Thử nghiệm: orientation classifier (Tier 3 — nhánh `exp/rectifier-corner-detection`)

Mục tiêu: thay việc **OCR lại 3-4 hướng** để dò upright (chậm, 6-10s) bằng **1 model nhỏ**
đoán hướng 0/90/180/270 → xoay 1 lần → OCR **đúng 1 lượt**.

⚠️ Nhánh THỬ NGHIỆM: tạm vượt ADR-012 ("không train") như corner-detector. Chưa merge `main`.

## Ý tưởng: DISTILLATION (chưng cất)
Dùng chính pipeline hiện tại (rectify + **OCR-search chính xác nhưng chậm**) để **TỰ GÁN NHÃN**
chiều upright cho mỗi ảnh gốc, rồi sinh 4 hướng làm data train cho CNN nhỏ học lại. Không gán tay.

- Nhãn = độ xoay CCW để về upright: `sample_C = upright.rotate(360-C)` → `sample_C.rotate(C)=upright`.
- Chỉ nhận nhãn khi hướng tốt **tách bạch rõ** với hướng nhì (bỏ ảnh mờ/nhập nhằng).

## Quy trình
```bash
PY=../../build/stage/runtime/python.exe          # có torch+torchvision CPU
export PYTHONPATH="../../service;../../rectifier"
export DIP_RECTIFY_CORNER_FALLBACK=true

# 1) Sinh data (OCR tự gán nhãn upright → 4 hướng)
$PY synth.py --out data

# 2) Train MobileNetV3-small (4 lớp), CPU
$PY train.py --data data --epochs 25

# 3) Xuất ONNX + meta (thứ tự lớp → độ xoay, imgsz)
$PY export.py --weights runs/best.pt

# 4) Tích hợp: copy runs/orientation.onnx(+json) → service/models/, bật DIP_ORIENT_CLASSIFIER=true
```

## Tích hợp (đã nối sẵn, mặc định TẮT)
- `app/cv/orient_model.py` — `OrientationClassifier` (onnxruntime CPU).
- `app/ocr/orient.py` — `OrientingOcr` nhận classifier: đủ tự tin → xoay 1 lần + OCR 1 lượt;
  ngược lại (thiếu tự tin / OCR ra kém) → **rơi về OCR-search cũ** → không bao giờ tệ hơn.
- `app/ocr/factory.py` + `settings.py` — cờ `DIP_ORIENT_CLASSIFIER`, `DIP_ORIENT_MODEL`,
  `DIP_ORIENT_MIN_CONF` (mặc định 0.75).

## Giới hạn / lưu ý
- Data nền tảng ~100 ảnh (samples + real_images) → nhờ transfer-learning (MobileNetV3 pretrained)
  + augment (KHÔNG xoay, vì xoay là nhãn) để bù ít ảnh. Val cao chưa chắc tốt thật → đánh giá ảnh thật.
- Classifier chỉ QUYẾT hướng; recognition vẫn VietOCR. An toàn nhờ fallback OCR-search.
