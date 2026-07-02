"""Nắn hướng ảnh 0/90/180/270° (DEC-009) — bọc quanh một OcrEngine.

Ý tưởng: chiều ĐÚNG là chiều mà OCR đọc ra **nhiều chữ ngang + confidence cao nhất**.
Thích ứng: nếu OCR ở 0° đã tốt thì dùng luôn (1 lần OCR); chỉ khi 0° kém mới thử thêm
90/180/270 và chọn chiều điểm cao nhất. Không cần model/OpenCV — chỉ xoay ảnh (PIL).
"""
from __future__ import annotations

from typing import Any

from app.ocr.types import OcrLine


class OrientingOcr:
    def __init__(self, base: Any, enabled: bool = True,
                 classifier: Any = None, min_conf: float = 0.75) -> None:
        self._base = base
        self._enabled = enabled
        self._clf = classifier          # OrientationClassifier (tuỳ chọn) — xoay 1 lần, khỏi dò 4×
        self._min_conf = min_conf

    @property
    def backend_name(self) -> str:
        """Tên engine recognition thật bên trong (VietOcrEngine/RapidOcrEngine/StubOcrEngine)
        — phơi qua /version để phát hiện khi bị lùi backend (vd VietOCR lỗi → Rapid mất dấu)."""
        return type(self._base).__name__

    def recognize(self, image: Any, assume_upright: bool = False, out: dict | None = None) -> list[OcrLine]:
        # `out` (tuỳ chọn, dict rỗng do caller tạo mỗi request → an toàn đa luồng): nhận ẢNH
        # ĐÃ CHỌN (đã xoay) mà `lines` thuộc về — để annotate box cho khớp (returnImage=annotated).
        def done(lines: list[OcrLine], img: Any) -> list[OcrLine]:
            if out is not None:
                out["image"] = img
            return lines

        # 1) Client khẳng định ảnh đã đúng chiều → 1 lượt, khỏi dò.
        if assume_upright:
            return done(self._base.recognize(image), image)

        # 2) Có orientation classifier + đủ tự tin → xoay 1 lần theo dự đoán, OCR 1 lượt.
        #    Tin classifier khi kết quả trông ĐÚNG CHIỀU (đa số box NGANG) — KHÔNG dùng
        #    good_enough ở đây vì ngưỡng conf 0.7 hay trượt oan trên thẻ có watermark (sẽ dò
        #    lại thừa, mất lợi ích). Chỉ khi trông vẫn nằm nghiêng (classifier sai thô) mới
        #    rơi xuống OCR-search bên dưới.
        if self._clf is not None and self._enabled:
            pred = self._clf.predict(image)
            if pred is not None and pred[1] >= self._min_conf:
                angle = pred[0]
                img = image if angle % 360 == 0 else image.rotate(angle, expand=True)
                lines = self._base.recognize(img)
                if self._looks_upright(lines):
                    return done(lines, img)

        # 3) OCR-search (fallback / khi không có classifier): 0° rồi dò theo TRỤC + dừng sớm.
        lines = self._base.recognize(image)
        if not self._enabled or self._good_enough(lines):
            return done(lines, image)
        best_score, best_lines, best_img = self._score(lines), lines, image
        for angle in self._angle_order(lines):
            rimg = image.rotate(angle, expand=True)             # PIL CCW, không cắt
            cand = self._base.recognize(rimg)
            score = self._score(cand)
            if score > best_score:
                best_score, best_lines, best_img = score, cand, rimg
            if self._good_enough(cand):
                break              # chiều này đã tốt → khỏi thử nốt (ảnh upside-down không đạt)
        return done(best_lines, best_img)

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
    def _looks_upright(lines: list[OcrLine]) -> bool:
        """Kết quả OCR trông ĐÚNG CHIỀU chưa: có chữ + đa số box NGANG (chữ ngang = đúng
        trục). Bắt được lỗi classifier xoay lệch 90/270 (box thành dọc); 0↔180 do classifier
        tự phân biệt (đã train). Lỏng hơn good_enough (không đòi conf cao) để 1-lượt ăn ngay."""
        if len(lines) < 3:
            return False
        horiz = sum(1 for l in lines if l.w >= l.h)
        return horiz >= 0.6 * len(lines)

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
