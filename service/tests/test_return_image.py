"""returnImage: encode/vẽ box + PipelineEngine._maybe_image (không cần model)."""
from __future__ import annotations

import base64
import io
from types import SimpleNamespace

from PIL import Image

from app.cv.annotate import draw_ocr_boxes, encode_jpeg_b64
from app.ocr.types import OcrLine
from app.pipeline.engine import PipelineEngine


def _img(w=400, h=250):
    return Image.new("RGB", (w, h), (200, 200, 200))


def test_encode_jpeg_b64_is_valid_jpeg():
    b = encode_jpeg_b64(_img())
    raw = base64.b64decode(b)
    im = Image.open(io.BytesIO(raw))
    assert im.format == "JPEG"


def test_encode_downscales_when_too_big():
    b = encode_jpeg_b64(_img(4000, 3000), max_side=1600)
    im = Image.open(io.BytesIO(base64.b64decode(b)))
    assert max(im.size) == 1600


def test_draw_boxes_keeps_size():
    lines = [OcrLine("x", 10, 20, 100, 30, 0.9)]
    out = draw_ocr_boxes(_img(), lines)
    assert out.size == (400, 250)


def _ctx(**opts):
    return SimpleNamespace(
        options={"returnImage": opts.get("returnImage", "none")},
        image_rectified=opts.get("image_rectified", _img()),
        ocr_image=opts.get("ocr_image"),
        ocr_lines=opts.get("ocr_lines", []),
    )


def test_maybe_image_none_default():
    assert PipelineEngine._maybe_image(_ctx()) is None


def test_maybe_image_none_when_no_rectified():
    assert PipelineEngine._maybe_image(_ctx(returnImage="rectified", image_rectified=None)) is None


def test_maybe_image_rectified():
    p = PipelineEngine._maybe_image(_ctx(returnImage="rectified"))
    assert p is not None and p.kind == "rectified" and len(p.base64) > 0


def test_maybe_image_annotated_with_boxes():
    lines = [OcrLine("a", 5, 5, 80, 20, 0.9)]
    p = PipelineEngine._maybe_image(_ctx(returnImage="annotated", ocr_lines=lines))
    assert p is not None and p.kind == "annotated"
    Image.open(io.BytesIO(base64.b64decode(p.base64)))  # decode được
