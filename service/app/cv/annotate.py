"""Tiện ích trả ảnh xử lý qua API (returnImage): encode JPEG→base64 + vẽ box OCR.

Dùng PIL (không cần cv2). Giảm cạnh dài trước khi encode để payload base64 không quá lớn.
"""
from __future__ import annotations

import base64
import io
from typing import Any


def encode_jpeg_b64(image: Any, quality: int = 85, max_side: int = 1600) -> str:
    im = image.convert("RGB")
    w, h = im.size
    if max(w, h) > max_side:
        s = max_side / max(w, h)
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def draw_ocr_boxes(image: Any, lines: list) -> Any:
    """Vẽ hộp bao (đỏ) của từng dòng OCR lên bản sao ảnh — để soi detect/nắn."""
    from PIL import ImageDraw
    im = image.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    for ln in lines:
        x, y, w, h = float(ln.x), float(ln.y), float(ln.w), float(ln.h)
        d.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=2)
    return im
