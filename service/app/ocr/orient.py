"""Nắn hướng ảnh 0/90/180/270° (DEC-009) — bọc quanh một OcrEngine.

Ý tưởng: chiều ĐÚNG là chiều mà OCR đọc ra **nhiều chữ ngang + confidence cao nhất**.
Thích ứng: nếu OCR ở 0° đã tốt thì dùng luôn (1 lần OCR); chỉ khi 0° kém mới thử thêm
90/180/270 và chọn chiều điểm cao nhất. Không cần model/OpenCV — chỉ xoay ảnh (PIL).
"""
from __future__ import annotations

from typing import Any

from app.ocr.types import OcrLine


class OrientingOcr:
    def __init__(self, base: Any, enabled: bool = True) -> None:
        self._base = base
        self._enabled = enabled

    def recognize(self, image: Any) -> list[OcrLine]:
        lines = self._base.recognize(image)
        if not self._enabled or self._good_enough(lines):
            return lines

        # 0° chưa đạt → thử 90/180/270 và chọn chiều có ĐIỂM cao nhất. Phải recognize từng
        # chiều vì chỉ confidence mới phân biệt được chiều đúng vs lộn ngược (hình học box
        # KHÔNG phân biệt 90↔270, 0↔180). Đây là ca ảnh xoay (ít gặp khi chụp qua app).
        best_score, best_lines = self._score(lines), lines
        for angle in (90, 180, 270):
            cand = self._base.recognize(image.rotate(angle, expand=True))  # PIL CCW, không cắt
            score = self._score(cand)
            if score > best_score:
                best_score, best_lines = score, cand
        return best_lines

    @staticmethod
    def _good_enough(lines: list[OcrLine]) -> bool:
        """0° coi là đúng nếu đã có đủ nhiều dòng và confidence cao (ảnh thẳng)."""
        if len(lines) < 6:
            return False
        avg = sum(l.confidence for l in lines) / len(lines)
        return avg >= 0.7

    @staticmethod
    def _score(lines: list[OcrLine]) -> float:
        """Điểm chiều: confidence, ưu tiên box NGANG (chữ đúng chiều thì rộng > cao)."""
        return sum(l.confidence * (1.0 if l.w >= l.h else 0.25) for l in lines)
