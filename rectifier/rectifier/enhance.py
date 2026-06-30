"""Tăng cường ảnh: CLAHE, sharpen, noise reduction, resize-cap. Thuần OpenCV."""
from __future__ import annotations

import cv2
import numpy as np


def clahe(image: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    """CLAHE trên kênh L (LAB) — tăng tương phản cục bộ, giữ màu."""
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid)).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)


def sharpen(image: np.ndarray, amount: float = 1.0, radius: int = 3) -> np.ndarray:
    """Unsharp mask: làm sắc nét nội dung."""
    blur = cv2.GaussianBlur(image, (0, 0), radius)
    return cv2.addWeighted(image, 1 + amount, blur, -amount, 0)


def denoise(image: np.ndarray, strength: int = 5) -> np.ndarray:
    """Khử nhiễu nhẹ (bilateral — nhanh hơn NlMeans, giữ cạnh)."""
    return cv2.bilateralFilter(image, d=5, sigmaColor=strength * 10, sigmaSpace=strength * 2)


def resize_cap(image: np.ndarray, out_long: int) -> np.ndarray:
    """Giới hạn cạnh dài (không phóng to) để khống chế kích thước output."""
    h, w = image.shape[:2]
    if max(h, w) <= out_long:
        return image
    s = out_long / max(h, w)
    return cv2.resize(image, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
