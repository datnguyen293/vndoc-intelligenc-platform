"""Test pipeline nắn ảnh — sinh ảnh tổng hợp (tài liệu chụp nghiêng) rồi kiểm chứng.

Không cần Internet, không cần ảnh mẫu ngoài: dựng một "tài liệu" sáng trên nền tối,
warp phối cảnh để giả lập ảnh chụp nghiêng, rồi yêu cầu Rectifier nắn lại.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from PIL import Image

from rectifier import Rectifier, available_presets, preset, rectify_image
from rectifier.config import RectifyConfig


def _make_skewed_doc(w=900, h=1200, ar="portrait") -> Image.Image:
    """Nền tối + tài liệu sáng có vài 'dòng chữ', đã warp phối cảnh (nghiêng)."""
    canvas = np.full((h, w, 3), 30, dtype=np.uint8)  # nền tối
    doc = np.full((600, 420, 3), 240, dtype=np.uint8)  # tài liệu sáng (dọc)
    for y in range(60, 560, 70):                       # vài dòng "chữ"
        cv2.rectangle(doc, (40, y), (380, y + 28), (40, 40, 40), -1)
    dh, dw = doc.shape[:2]
    src = np.float32([[0, 0], [dw, 0], [dw, dh], [0, dh]])
    # tứ giác đích lệch (mô phỏng chụp nghiêng), nằm gọn trong canvas
    dst = np.float32([[180, 120], [760, 60], [820, 1080], [120, 1010]])
    m = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(doc, m, (w, h), borderValue=(30, 30, 30))
    mask = cv2.warpPerspective(np.full((dh, dw), 255, np.uint8), m, (w, h))
    canvas[mask > 0] = warped[mask > 0]
    return Image.fromarray(canvas)


def test_presets_available():
    names = available_presets()
    assert {"general", "id_card", "document", "receipt", "photo"} <= set(names)


def test_preset_overrides():
    cfg = preset("id_card", out_long=2400, denoise=True)
    assert cfg.ar_min == 1.2 and cfg.out_long == 2400 and cfg.denoise is True


def test_preset_invalid_name():
    with pytest.raises(ValueError):
        preset("khong_ton_tai")


def test_preset_invalid_field():
    with pytest.raises(ValueError):
        preset("general", khong_co_field=1)


def test_rectify_finds_and_straightens():
    img = _make_skewed_doc()
    res = Rectifier(preset("general")).rectify(img)
    assert res.found is True
    assert res.corners is not None and len(res.corners) == 4
    # kết quả phải gần chữ nhật dọc (cao > rộng) và không rỗng
    ow, oh = res.image.size
    assert ow > 50 and oh > 50
    assert oh > ow  # tài liệu dọc → output dọc


def test_rectify_disabled_passthrough():
    img = _make_skewed_doc()
    cfg = RectifyConfig(enabled=False)
    res = Rectifier(cfg).rectify(img)
    assert res.found is False
    # passthrough chỉ resize-cap, giữ nguyên hướng/tỉ lệ ảnh gốc
    assert abs(res.image.size[0] / res.image.size[1] - img.size[0] / img.size[1]) < 0.01


def test_rectify_already_flat_is_passthrough():
    """Ảnh đã phẳng + lấp gần kín khung → không warp (found=False)."""
    flat = np.full((800, 600, 3), 235, np.uint8)
    for y in range(40, 760, 60):
        cv2.rectangle(flat, (30, y), (570, y + 24), (50, 50, 50), -1)
    res = Rectifier(preset("general")).rectify(Image.fromarray(flat))
    assert res.found is False


def test_debug_captures_stages():
    img = _make_skewed_doc()
    res = Rectifier(preset("general")).rectify(img, debug=True)
    assert "input" in res.stages and "output" in res.stages
    assert set(res.timings) & {"segment", "perspective"}


def test_rectify_image_helper(tmp_path):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _make_skewed_doc().save(src)
    res = rectify_image(str(src), str(dst), preset="document")
    assert dst.exists() and res.image.size[0] > 0
