"""Regression: _order_points phải BỀN với thẻ nghiêng ~45°.

Bug cũ (sum/diff): ở góc xoay ~45°, argmax(sum) và argmax(diff) trỏ CÙNG một đỉnh →
br≡bl, một góc thật bị bỏ → tứ giác suy biến → warpPerspective ra ảnh trống → OCR mất
chữ (warnings=ocr_no_text). Xem app/cv/corner.py.
"""
from __future__ import annotations

import numpy as np

from app.cv.corner import _order_points, _quad_area


def _rot(cx, cy, w, h, deg):
    """4 góc của hình chữ nhật w×h tâm (cx,cy) xoay `deg` độ (thứ tự bất kỳ)."""
    r = np.deg2rad(deg)
    c, s = np.cos(r), np.sin(r)
    base = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], float)
    m = np.array([[c, -s], [s, c]])
    return (base @ m.T) + [cx, cy]


def test_order_points_no_degenerate_at_45deg():
    """Ca gây bug thật (thẻ trung-hieu.jpeg nghiêng ~45°): 4 góc phải PHÂN BIỆT."""
    pts = np.array([[288, 740], [655, 433], [846, 676], [535, 1011]], float)
    rect = _order_points(pts)
    # 4 đỉnh phải đôi một khác nhau (bug cũ cho br≡bl)
    uniq = {(round(x), round(y)) for x, y in rect}
    assert len(uniq) == 4, f"tứ giác suy biến: {rect.tolist()}"
    # diện tích phải xấp xỉ tứ giác gốc (không bị co về 0/nửa)
    assert abs(_quad_area(rect) - _quad_area(pts)) < 1.0


def test_order_points_all_angles_landscape():
    """Mọi góc xoay 0..350°: luôn ra 4 đỉnh phân biệt, cạnh trên≈dưới, trái≈phải."""
    for deg in range(0, 360, 5):
        pts = _rot(500, 500, 300, 190, deg)
        rect = _order_points(pts)
        uniq = {(round(x, 1), round(y, 1)) for x, y in rect}
        assert len(uniq) == 4, f"deg={deg} suy biến: {rect.tolist()}"
        tl, tr, br, bl = rect
        top = np.linalg.norm(tr - tl)
        bottom = np.linalg.norm(br - bl)
        left = np.linalg.norm(bl - tl)
        right = np.linalg.norm(br - tr)
        # cạnh đối phải xấp xỉ nhau (thứ tự đúng quanh chu vi, không chéo)
        assert abs(top - bottom) < 1.0, f"deg={deg} top≠bottom"
        assert abs(left - right) < 1.0, f"deg={deg} left≠right"


def test_order_points_first_is_top_left():
    """Đỉnh đầu (TL) là đỉnh 'trên-trái' nhất (min x+y) cho thẻ gần thẳng."""
    pts = np.array([[100, 100], [400, 110], [405, 300], [95, 290]], float)
    rect = _order_points(pts)
    assert tuple(np.round(rect[0])) == (100, 100)
