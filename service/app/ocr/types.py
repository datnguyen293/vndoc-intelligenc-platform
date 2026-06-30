"""Kiểu dữ liệu OCR trung gian — một dòng/cụm chữ kèm vị trí."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OcrLine:
    """Một cụm chữ OCR: text + hộp bao trục (axis-aligned) + độ tin cậy."""

    text: str
    x: float
    y: float
    w: float
    h: float
    confidence: float = 1.0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    @classmethod
    def from_polygon(cls, box, text: str, confidence: float = 1.0) -> "OcrLine":
        """Tạo từ polygon 4 điểm [[x,y],...] (định dạng PaddleOCR)."""
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = min(xs), min(ys)
        return cls(text=text, x=float(x), y=float(y),
                   w=float(max(xs) - x), h=float(max(ys) - y),
                   confidence=float(confidence))
