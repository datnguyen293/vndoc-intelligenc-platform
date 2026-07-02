"""Đánh giá orientation classifier trên ẢNH THẬT qua pipeline (rectify → xoay đã biết → đoán).

Cho mỗi ảnh: rectify → coi output là base; xoay CW 0/90/180/270 (giả lập ảnh vào ở 4 hướng),
classifier phải đoán đúng góc CCW để về base. Tính accuracy + confidence trung bình.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "service"))

os.environ.setdefault("DIP_RECTIFY_CORNER_FALLBACK", "true")
from app.cv import build_preprocessors                       # noqa: E402
from app.cv.orient_model import OrientationClassifier        # noqa: E402

clf = OrientationClassifier(HERE / "runs" / "orientation.onnx")
det, rect = build_preprocessors(True)

srcs = []
for d in [REPO / "service" / "samples", REPO / "experiments" / "corner-detector" / "real_images"]:
    srcs += [p for p in d.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
# lấy mẫu rải đều ~24 ảnh cho nhanh
srcs = srcs[:: max(1, len(srcs) // 24)]

tot = ok = 0
conf_sum = 0.0
wrong = []
for p in srcs:
    try:
        pil = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        base = rect.rectify(pil, det.detect(pil))
    except Exception:
        continue
    for applied in (0, 90, 180, 270):
        # ảnh "vào" bị xoay CW `applied` → cần CCW `applied` để về base
        img = base if applied == 0 else base.rotate(360 - applied, expand=True)
        pred = clf.predict(img)
        if pred is None:
            continue
        tot += 1
        conf_sum += pred[1]
        if pred[0] == applied:
            ok += 1
        else:
            wrong.append(f"{p.parent.name}/{p.name} applied={applied} pred={pred[0]}({pred[1]:.2f})")

print(f"ẢNH THẬT: accuracy = {ok}/{tot} = {ok/max(tot,1):.3f}  conf_tb = {conf_sum/max(tot,1):.3f}")
if wrong:
    print("SAI:")
    for w in wrong[:20]:
        print("  " + w)
