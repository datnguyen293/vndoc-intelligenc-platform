"""Adapter RapidOCR — PP-OCR (PaddleOCR) chạy trên **ONNX Runtime** (ADR-003).

Ưu điểm so với cài paddlepaddle: model đóng gói sẵn (không tải từ Baidu), cài 1 lệnh,
chạy đa nền tảng. Phần recognition mặc định là PP-OCRv4 đa ngữ (đọc được Latin + dấu
tiếng Việt ở mức khá). Để đạt độ chính xác cao nhất có thể thay rec model bằng VietOCR
sau — vẫn sau cùng một Protocol OcrEngine.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ocr.types import OcrLine

log = logging.getLogger("dip.ocr")


class RapidOcrEngine:
    def __init__(self) -> None:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        self._np = np
        self._ocr = RapidOCR()
        log.info("RapidOCR (ONNX) sẵn sàng")

    def recognize(self, image: Any) -> list[OcrLine]:
        arr = self._np.array(image)  # PIL.Image -> ndarray
        result, _elapse = self._ocr(arr)
        lines: list[OcrLine] = []
        if not result:
            return lines
        for box, text, score in result:
            if text and text.strip():
                lines.append(OcrLine.from_polygon(box, text.strip(), float(score)))
        return lines
