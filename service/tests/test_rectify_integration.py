"""Tích hợp package `rectifier` vào pipeline qua build_preprocessors.

(Logic nắn ảnh có test riêng trong project ../rectifier; ở đây chỉ kiểm khâu tích hợp.)
"""
import numpy as np
import pytest

pytest.importorskip("rectifier")
pytest.importorskip("cv2")
import cv2  # noqa: E402
from PIL import Image  # noqa: E402

from app.cv import build_preprocessors  # noqa: E402


def _skewed_card() -> Image.Image:
    arr = np.full((420, 640, 3), 25, dtype=np.uint8)
    cv2.fillConvexPoly(arr, np.array([[90, 70], [580, 120], [540, 380], [70, 330]]),
                       (235, 235, 235))
    return Image.fromarray(arr)


def test_build_preprocessors_uses_rectifier():
    det, rect = build_preprocessors(card_detect=True)
    assert det.detect(_skewed_card()) is None  # noop detector
    out = rect.rectify(_skewed_card(), None)    # rectifier package nắn ảnh nghiêng
    assert isinstance(out, Image.Image) and out.size[0] > 10


def test_build_preprocessors_disabled_passthrough():
    _, rect = build_preprocessors(card_detect=False)
    img = _skewed_card()
    out = rect.rectify(img, None)  # enabled=False → chỉ resize-cap, không warp
    assert isinstance(out, Image.Image)


def test_preset_id_card_constraints():
    import rectifier
    cfg = rectifier.preset("id_card")
    assert cfg.ar_min == 1.2 and cfg.ar_max == 2.3 and cfg.rotate_landscape is True
