"""Orientation classifier (thử nghiệm) — đoán hướng 0/90/180/270 bằng CNN nhỏ (ONNX/CPU).

Thay việc OCR lại tới 3-4 hướng để dò upright (chậm) bằng MỘT lần infer nhẹ: xoay ảnh theo
dự đoán rồi OCR đúng 1 lượt. OrientingOcr vẫn giữ OCR-search làm FALLBACK khi model thiếu
tự tin hoặc kết quả OCR kém → không bao giờ tệ hơn hành vi cũ. Mặc định TẮT.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("dip.cv.orient")


class OrientationClassifier:
    def __init__(self, onnx_path: Any) -> None:
        import onnxruntime as ort
        p = Path(onnx_path)
        meta = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
        self.classes = [int(c) for c in meta["classes"]]   # index → độ xoay CCW về upright
        self.imgsz = int(meta.get("imgsz", 160))
        self.mean = np.array(meta.get("mean", [0.485, 0.456, 0.406]), np.float32)
        self.std = np.array(meta.get("std", [0.229, 0.224, 0.225]), np.float32)
        self.sess = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name

    def predict(self, image: Any) -> tuple[int, float] | None:
        """Trả (angle, confidence) — angle ∈ {0,90,180,270}; None nếu lỗi."""
        try:
            im = image.convert("RGB").resize((self.imgsz, self.imgsz))
            arr = (np.asarray(im, np.float32) / 255.0 - self.mean) / self.std
            blob = arr.transpose(2, 0, 1)[None].astype(np.float32)
            logits = self.sess.run(None, {self.inp: blob})[0][0]
            e = np.exp(logits - logits.max())
            probs = e / e.sum()
            idx = int(probs.argmax())
            return self.classes[idx], float(probs[idx])
        except Exception as exc:  # noqa: BLE001 — lỗi model KHÔNG được phá pipeline
            log.warning("orientation classifier lỗi (%s) → bỏ qua, dùng OCR-search", exc)
            return None
