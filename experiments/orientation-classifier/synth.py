"""Sinh dữ liệu train orientation-classifier (nhánh exp, tạm vượt ADR-012).

Ý tưởng DISTILLATION: dùng chính pipeline hiện tại (rectify + OCR-search chính xác nhưng
CHẬM) để TỰ GÁN NHÃN chiều upright cho mỗi ảnh gốc, rồi sinh 4 hướng (0/90/180/270) làm
dữ liệu train cho một CNN NHỎ (nhanh) học lại — sau này thay OCR-search 4× bằng 1 lần infer.

Nhãn = số độ xoay CCW để về upright: sample_C = upright.rotate(360-C) → sample_C.rotate(C)=upright.

Chạy:
  PY=../../build/stage/runtime/python.exe
  PYTHONPATH=../../service;../../rectifier  $PY synth.py --out data
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def _score(lines) -> float:
    # Giống app.ocr.orient._score: confidence, ưu tiên box NGANG (chữ đúng chiều rộng>cao).
    return sum(l.confidence * (1.0 if l.w >= l.h else 0.25) for l in lines)


def _sources() -> list[Path]:
    out: list[Path] = []
    for d in [REPO / "service" / "samples", REPO / "experiments" / "corner-detector" / "real_images"]:
        if d.exists():
            for p in d.rglob("*"):
                if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                    out.append(p)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "data"))
    ap.add_argument("--min-lines", type=int, default=4)
    ap.add_argument("--min-margin", type=float, default=1.2, help="điểm hướng tốt / hướng nhì ≥ margin mới nhận nhãn")
    ap.add_argument("--val-every", type=int, default=6, help="cứ N ảnh lấy 1 ảnh cho val")
    args = ap.parse_args()

    os.environ.setdefault("DIP_RECTIFY_CORNER_FALLBACK", "true")
    from app.cv import build_preprocessors
    from app.ocr import create_ocr_engine

    det, rect = build_preprocessors(True)
    base = create_ocr_engine()
    # Lấy engine THẬT bên trong OrientingOcr để tự điều khiển việc xoay.
    inner = getattr(base, "_base", base)
    print("OCR backend:", type(inner).__name__)

    out = Path(args.out)
    for split in ("train", "val"):
        for c in (0, 90, 180, 270):
            (out / split / str(c)).mkdir(parents=True, exist_ok=True)

    srcs = _sources()
    print(f"{len(srcs)} ảnh nguồn")
    kept = skipped = 0
    for i, p in enumerate(srcs):
        try:
            pil = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
            card = rect.rectify(pil, det.detect(pil))          # ảnh đã nắn (card-filling)
            # Chấm điểm 4 hướng → hướng điểm cao nhất = upright.
            scored = []
            for ang in (0, 90, 180, 270):
                im = card if ang == 0 else card.rotate(ang, expand=True)
                scored.append((_score(inner.recognize(im)), ang, im))
            scored.sort(key=lambda t: t[0], reverse=True)
            top, second = scored[0], scored[1]
            # Nhãn tin cậy: điểm hướng tốt phải TÁCH BẠCH rõ với hướng nhì (tránh ảnh mờ/nhập nhằng).
            if top[0] <= 0 or (second[0] > 0 and top[0] / max(second[0], 1e-6) < args.min_margin):
                skipped += 1
                continue
            upright = top[2]                                    # PIL đã ở upright
            split = "val" if (i % args.val_every == 0) else "train"
            stem = f"{p.parent.name}_{p.stem}"
            for c in (0, 90, 180, 270):
                sample = upright if c == 0 else upright.rotate(360 - c, expand=True)
                sample.save(out / split / str(c) / f"{stem}.jpg", quality=92)
            kept += 1
            if kept % 10 == 0:
                print(f"  [{i+1}/{len(srcs)}] kept={kept} skipped={skipped}")
        except Exception as exc:  # noqa: BLE001
            print(f"  lỗi {p.name}: {exc}")
            skipped += 1
    print(f"XONG: {kept} ảnh upright × 4 hướng, bỏ {skipped}. Data ở {out}")


if __name__ == "__main__":
    main()
