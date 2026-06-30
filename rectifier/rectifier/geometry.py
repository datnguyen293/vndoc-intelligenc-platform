"""Hình học: mask → 4 góc → tinh chỉnh góc → warp phối cảnh → xoay/deskew/padding.

Thuần OpenCV/NumPy — không cần model, chạy offline.
"""
from __future__ import annotations

import math

import cv2
import numpy as np


def order_points(pts: np.ndarray) -> np.ndarray:
    """Sắp 4 điểm theo thứ tự TL, TR, BR, BL."""
    pts = np.asarray(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # TL (x+y nhỏ nhất)
    rect[2] = pts[np.argmax(s)]   # BR
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]   # TR (x-y lớn nhất → y-x nhỏ nhất)
    rect[3] = pts[np.argmax(d)]   # BL
    return rect


def quad_wh(rect: np.ndarray) -> tuple[float, float]:
    """Chiều rộng/cao trung bình của tứ giác đã sắp xếp."""
    tl, tr, br, bl = rect
    w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    return float(w), float(h)


def aspect_ratio(pts: np.ndarray) -> float:
    """Tỉ lệ cạnh dài / cạnh ngắn (luôn ≥ 1)."""
    w, h = quad_wh(order_points(pts))
    return max(w, h) / max(1e-6, min(w, h))


def skew_deg(pts: np.ndarray) -> float:
    """Độ nghiêng lớn nhất của cạnh trên/trái so với phương ngang/dọc (độ)."""
    tl, tr, _br, bl = order_points(pts)
    top = abs(math.degrees(math.atan2(tr[1] - tl[1], tr[0] - tl[0])))
    left = abs(math.degrees(math.atan2(bl[1] - tl[1], bl[0] - tl[0])) - 90)
    return max(top, left)


def mask_to_corners(mask: np.ndarray, min_area_ratio: float = 0.2) -> np.ndarray | None:
    """Mask lớn nhất → polygon fitting → 4 góc. approxPolyDP, fallback minAreaRect."""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    area_img = mask.shape[0] * mask.shape[1]
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < min_area_ratio * area_img:
        return None
    peri = cv2.arcLength(c, True)
    for eps in (0.02, 0.04, 0.06, 0.08):
        approx = cv2.approxPolyDP(c, eps * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return approx.reshape(4, 2).astype("float32")
    # fallback: chữ nhật xoay nhỏ nhất bao contour
    box = cv2.boxPoints(cv2.minAreaRect(c))
    return box.astype("float32")


def refine_corners(gray: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Tinh chỉnh góc xuống mức sub-pixel bằng cornerSubPix."""
    pts = np.asarray(corners, dtype="float32").reshape(-1, 1, 2)
    try:
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
        cv2.cornerSubPix(gray, pts, (7, 7), (-1, -1), crit)
    except cv2.error:
        pass
    return pts.reshape(-1, 2)


def four_point_transform(image: np.ndarray, corners: np.ndarray,
                         margin: float = 0.0) -> np.ndarray:
    """Warp phối cảnh 4 góc về chữ nhật thẳng (loại nền ngoài quad)."""
    rect = order_points(corners)
    if margin > 0:  # nới ra ngoài quanh tâm để khỏi cắt cụt nội dung sát mép
        c = rect.mean(axis=0)
        rect = c + (rect - c) * (1.0 + margin)
        rect[:, 0] = np.clip(rect[:, 0], 0, image.shape[1] - 1)
        rect[:, 1] = np.clip(rect[:, 1], 0, image.shape[0] - 1)
    w, h = quad_wh(rect)
    max_w, max_h = int(round(w)), int(round(h))
    if max_w < 10 or max_h < 10:
        return image
    dst = np.array([[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
                   dtype="float32")
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, m, (max_w, max_h))


def auto_rotate_landscape(image: np.ndarray) -> np.ndarray:
    """Xoay 90° nếu ảnh đang dọc → ngang (chuẩn hóa landscape)."""
    h, w = image.shape[:2]
    if h > w:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image


def deskew(image: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """Sửa nghiêng nhỏ còn lại: ước lượng góc bằng minAreaRect của vùng foreground."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(th > 0))
    if coords.shape[0] < 50:
        return image
    angle = cv2.minAreaRect(coords[:, ::-1].astype("float32"))[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    if abs(angle) < 0.3 or abs(angle) > max_angle:
        return image  # gần thẳng hoặc bất thường → bỏ qua
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image, m, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def add_padding(image: np.ndarray, pad_ratio: float = 0.02,
                color: tuple = (255, 255, 255)) -> np.ndarray:
    """Adaptive padding: viền tỉ lệ theo kích thước (lề quanh nội dung)."""
    h, w = image.shape[:2]
    p = max(2, int(round(min(h, w) * pad_ratio)))
    return cv2.copyMakeBorder(image, p, p, p, p, cv2.BORDER_CONSTANT, value=color)
