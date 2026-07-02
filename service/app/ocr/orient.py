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

    @property
    def backend_name(self) -> str:
        """Tên engine recognition thật bên trong (VietOcrEngine/RapidOcrEngine/StubOcrEngine)
        — phơi qua /version để phát hiện khi bị lùi backend (vd VietOCR lỗi → Rapid mất dấu)."""
        return type(self._base).__name__

    def recognize(self, image: Any, assume_upright: bool = False) -> list[OcrLine]:
        lines = self._base.recognize(image)
        # assume_upright: client (app) khẳng định ảnh đã đúng chiều (đã áp EXIF) → KHỎI dò,
        # tiết kiệm tới 3 lượt OCR. 0° đã đạt / tắt auto-orient cũng dừng luôn (1 lượt).
        if assume_upright or not self._enabled or self._good_enough(lines):
            return lines

        # 0° chưa đạt → thử các chiều còn lại và chọn ĐIỂM cao nhất. Phải recognize từng chiều
        # vì chỉ confidence mới phân biệt chiều đúng vs lộn ngược (hình học box KHÔNG phân biệt
        # 90↔270, 0↔180). Nhưng KHÔNG cần thử đủ 4: suy TRỤC chữ từ box ở 0° để thử đúng cặp
        # trước + DỪNG SỚM khi đạt → cắt ~1/2 số lượt (thường 2 thay vì 4).
        best_score, best_lines = self._score(lines), lines
        for angle in self._angle_order(lines):
            cand = self._base.recognize(image.rotate(angle, expand=True))  # PIL CCW, không cắt
            score = self._score(cand)
            if score > best_score:
                best_score, best_lines = score, cand
            if self._good_enough(cand):
                break              # chiều này đã tốt → khỏi thử nốt (ảnh upside-down không đạt)
        return best_lines

    @staticmethod
    def _angle_order(lines: list[OcrLine]) -> tuple[int, ...]:
        """Thứ tự thử hướng theo TRỤC chữ suy từ box ở 0° — tránh OCR đủ 4 hướng.

        Chữ NGANG (w≥h) đa số → ảnh chỉ có thể bị lộn 180° → thử 180 trước. Chữ DỌC (h>w)
        đa số → ảnh nằm nghiêng → thử 90/270 trước. Vẫn liệt kê ĐỦ các hướng (không dừng
        sớm được thì lần lượt thử hết) để không bỏ sót ca hiếm.
        """
        horiz = sum(1 for l in lines if l.w >= l.h)
        vert = len(lines) - horiz
        if not lines or horiz >= vert:
            return (180, 90, 270)
        return (90, 270, 180)

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
