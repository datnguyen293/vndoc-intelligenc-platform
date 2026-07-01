"""Stub cho các stage cần model thật (ADR-003/004/006).

Mục đích: cho khung chạy đầu-cuối. Khi gắn model thật, thay từng class bằng cài đặt
hiện thực cùng Protocol ở core/interfaces.py — pipeline không đổi.
"""
from __future__ import annotations

from typing import Any

from app.ocr.types import OcrLine


class StubQualityChecker:
    def check(self, image: Any) -> tuple[bool, dict[str, float]]:
        # Skeleton: luôn coi là đạt; bản thật đo blur/brightness/glare (FR-002).
        return True, {}


class StubDetector:
    def detect(self, image: Any) -> Any:
        # Skeleton: chưa tìm khung; bản thật trả polygon 4 góc (OpenCV).
        return None


class StubRectifier:
    def rectify(self, image: Any, polygon: Any) -> Any:
        # Skeleton: trả nguyên ảnh; bản thật warp + chuẩn hóa hướng (DEC-009).
        return image


class StubClassifier:
    """Phân loại tạm bằng docTypeHint cho tới khi có phân loại thuần luật (ADR-008)."""

    def __init__(self, known_types: set[str]) -> None:
        self._known = known_types

    def classify(self, lines: Any, hint: str | None = None) -> tuple[str, float]:
        if hint and hint in self._known:
            return hint, 0.5  # độ tin cậy thấp vì chỉ dựa hint
        return "unknown", 0.0


class StubStructuredReader:
    def read(
        self, image: Any, doc_type: str, lines: Any = None, image_alt: Any = None
    ) -> tuple[dict[str, str], list[str]]:
        # Skeleton: chưa giải mã QR/MRZ/barcode (ADR-006).
        return {}, []

    def identify(self, image: Any, hint: str | None = None, image_alt: Any = None):
        # Skeleton: không có QR → luôn rơi về đường OCR.
        return None


class StubOcrEngine:
    """OCR rỗng — dùng khi chưa cài PaddleOCR. Trả [] để pipeline vẫn chạy."""

    def recognize(self, image: Any) -> list[OcrLine]:
        return []
