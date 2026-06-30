"""Unit test logic nắn hướng (OrientingOcr) — tất định, không cần model.

Mô phỏng: OCR chỉ đọc tốt (nhiều box ngang, confidence cao) khi ảnh ở chiều đúng
(angle == 0). OrientingOcr phải tự xoay tới chiều đó.
"""
from app.ocr.orient import OrientingOcr
from app.ocr.types import OcrLine


class _FakeImg:
    def __init__(self, angle: int = 0):
        self.angle = angle % 360

    def rotate(self, a, expand=False):
        return _FakeImg(self.angle + a)


class _AngleOcr:
    """Đọc tốt khi angle==0; ngược lại trả ít dòng, box dọc, confidence thấp."""

    def recognize(self, img):
        if getattr(img, "angle", 0) % 360 == 0:
            return [OcrLine("THẺ ĐẢNG VIÊN", 0, 0, 200, 28, 0.95) for _ in range(8)]
        return [OcrLine("xx", 0, 0, 10, 50, 0.2) for _ in range(3)]


def test_orient_finds_upright_from_rotated():
    eng = OrientingOcr(_AngleOcr())
    lines = eng.recognize(_FakeImg(90))  # ảnh xoay 90°
    assert lines and lines[0].text == "THẺ ĐẢNG VIÊN"
    assert len(lines) == 8


def test_orient_skips_search_when_already_good():
    eng = OrientingOcr(_AngleOcr())
    lines = eng.recognize(_FakeImg(0))  # ảnh thẳng → dùng luôn
    assert len(lines) == 8


def test_orient_disabled_passthrough():
    eng = OrientingOcr(_AngleOcr(), enabled=False)
    lines = eng.recognize(_FakeImg(90))  # tắt → không xoay, trả nguyên (kém)
    assert lines[0].text == "xx"
