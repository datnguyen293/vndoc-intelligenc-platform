"""Engine lai: RapidOCR (detection) + VietOCR (recognition) — ADR-004.

RapidOCR/ONNX lo *định vị dòng chữ* (PP detection), VietOCR (transformer/seq2seq
chuyên tiếng Việt) lo *đọc* → ra **đúng dấu tiếng Việt**. Import lười; factory fallback
nếu thiếu torch/vietocr.

Lần chạy đầu VietOCR tải weights (cần mạng) → copy sẵn sang máy offline khi triển khai.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ocr.types import OcrLine

log = logging.getLogger("dip.ocr")


class VietOcrEngine:
    def __init__(self, model_name: str = "vgg_seq2seq") -> None:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor

        self._np = np
        self._det = RapidOCR()  # chỉ dùng để lấy box (bỏ phần text của nó)

        cfg = Cfg.load_config_from_name(model_name)  # vgg_seq2seq nhẹ/nhanh cho CPU
        cfg["device"] = "cpu"
        cfg["predictor"]["beamsearch"] = False

        # Offline: nếu có weights cục bộ trong models_dir thì dùng, khỏi tải mạng.
        from app.settings import settings
        local = settings.models_dir / f"{model_name}.pth"
        if local.exists():
            cfg["weights"] = str(local)
            log.info("VietOCR dùng weights cục bộ: %s", local)

        self._rec = Predictor(cfg)
        log.info("VietOCR (%s) + RapidOCR-det sẵn sàng", model_name)

    def _boxes(self, arr) -> list:
        # Ưu tiên det-only để khỏi chạy recognition thừa của RapidOCR.
        try:
            res, _ = self._det(arr, use_det=True, use_cls=True, use_rec=False)
            if res:
                return list(res)
        except Exception:  # noqa: BLE001 — API đời cũ không có use_rec
            pass
        res, _ = self._det(arr)
        return [item[0] for item in res] if res else []

    def recognize(self, image: Any) -> list[OcrLine]:
        arr = self._np.array(image)
        boxes = self._boxes(arr)
        W, H = image.size

        crops, kept = [], []
        for box in boxes:
            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]
            x1, y1 = max(0, int(min(xs)) - 2), max(0, int(min(ys)) - 2)
            x2, y2 = min(W, int(max(xs)) + 2), min(H, int(max(ys)) + 2)
            if x2 <= x1 or y2 <= y1:
                continue
            crops.append(image.crop((x1, y1, x2, y2)))
            kept.append(box)

        if not crops:
            return []
        # Batch recognition — nhanh hơn nhiều so với gọi predict từng dòng (CPU).
        try:
            texts, probs = self._rec.predict_batch(crops, return_prob=True)
        except Exception:  # noqa: BLE001
            return []

        lines: list[OcrLine] = []
        for box, txt, prob in zip(kept, texts, probs):
            if txt and txt.strip():
                lines.append(OcrLine.from_polygon(box, txt.strip(), float(prob)))
        return lines
