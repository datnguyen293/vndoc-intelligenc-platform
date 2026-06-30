"""Adapter PaddleOCR — OCR thật (ADR-004: PaddleOCR detection + recognition).

Import lười: nếu chưa cài paddleocr/paddle thì factory sẽ fallback sang stub, service
vẫn chạy. Khi triển khai thật: pip install paddleocr paddlepaddle (model offline đặt
trong models_dir, tải sẵn trên máy có mạng rồi copy sang máy offline).
"""
from __future__ import annotations

import logging
from typing import Any

from app.ocr.types import OcrLine

log = logging.getLogger("dip.ocr")


class PaddleOcrEngine:
    def __init__(self, lang: str = "vi", use_angle_cls: bool = True) -> None:
        # Import nặng — chỉ thực hiện khi khởi tạo engine thật.
        import numpy as np  # noqa: F401  (đảm bảo có sẵn cho recognize)
        from paddleocr import PaddleOCR

        self._np = np
        self._ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, show_log=False)
        log.info("PaddleOCR sẵn sàng (lang=%s, angle_cls=%s)", lang, use_angle_cls)

    def recognize(self, image: Any) -> list[OcrLine]:
        arr = self._np.array(image)  # PIL.Image -> ndarray RGB
        result = self._ocr.ocr(arr, cls=True)
        lines: list[OcrLine] = []
        if not result:
            return lines
        page = result[0] or []
        for box, (text, conf) in page:
            if text and text.strip():
                lines.append(OcrLine.from_polygon(box, text.strip(), float(conf)))
        return lines
