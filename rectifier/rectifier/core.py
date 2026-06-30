"""Rectifier — orchestrator nắn chỉnh ảnh tài liệu chụp nghiêng/méo/xoay.

Luồng: Image → Segmentation → Largest Mask → Polygon Fitting → Corner Refinement →
Perspective → Auto Rotate → Adaptive Padding → Deskew → CLAHE → Sharpen → Output.

Mỗi stage bật/tắt qua RectifyConfig; có timing + bắt ảnh trung gian (debug).
"Nắn-khi-cần": ảnh đã phẳng + lấp khung → passthrough (khỏi xê dịch ảnh đã tốt).
Chạy hoàn toàn offline với backend `classic` (thuần OpenCV, không cần model).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image

from rectifier import enhance, geometry
from rectifier.config import RectifyConfig
from rectifier.segment import get_segmenter


@dataclass
class RectifyResult:
    image: Image.Image                    # ảnh kết quả (PIL RGB)
    found: bool                           # có nắn (tìm thấy tài liệu) hay passthrough
    corners: list | None = None           # 4 góc trên ảnh gốc (TL, TR, BR, BL)
    timings: dict = field(default_factory=dict)
    stages: dict = field(default_factory=dict)  # ảnh trung gian (chỉ khi debug)


class Rectifier:
    """Nắn ảnh về chữ nhật/hình vuông thẳng hàng.

    >>> from rectifier import Rectifier, preset
    >>> r = Rectifier(preset("general"))
    >>> result = r.rectify(Image.open("anh.jpg"))
    >>> result.image.save("anh_nan.jpg")
    """

    def __init__(self, config: RectifyConfig | None = None) -> None:
        self.cfg = config or RectifyConfig()
        self._seg = get_segmenter(self.cfg.segmenter, self.cfg.yolo_weights,
                                  self.cfg.min_area_ratio, self.cfg.grabcut_fallback)

    def rectify(self, image: Image.Image, debug: bool = False) -> RectifyResult:
        cfg = self.cfg
        rgb = np.array(image.convert("RGB"))
        timings: dict = {}
        stages: dict = {"input": rgb.copy()} if debug else {}

        if not cfg.enabled:
            out = enhance.resize_cap(rgb, cfg.out_long)
            return RectifyResult(Image.fromarray(out), False, timings=timings, stages=stages)

        # 1) Segmentation (ở độ phân giải nhỏ cho nhanh)
        t = time.perf_counter()
        h, w = rgb.shape[:2]
        scale = cfg.work / max(h, w) if max(h, w) > cfg.work else 1.0
        small = cv2.resize(rgb, (int(w * scale), int(h * scale))) if scale < 1 else rgb
        mask = self._seg.segment(small)
        timings["segment"] = self._ms(t)
        if debug and mask is not None:
            stages["mask"] = mask.copy()

        if mask is None:
            return self._passthrough(rgb, timings, stages)

        # 2) Largest mask → polygon fitting
        t = time.perf_counter()
        corners_s = geometry.mask_to_corners(mask, cfg.min_area_ratio)
        timings["polygon"] = self._ms(t)
        if corners_s is None:
            return self._passthrough(rgb, timings, stages)

        # validate tỉ lệ (nếu preset có ràng buộc) + nắn-khi-cần
        ar = geometry.aspect_ratio(corners_s)
        fill = cv2.contourArea(corners_s.astype("float32")) / (small.shape[0] * small.shape[1])
        if cfg.ar_min is not None and ar < cfg.ar_min:
            return self._passthrough(rgb, timings, stages)
        if cfg.ar_max is not None and ar > cfg.ar_max:
            return self._passthrough(rgb, timings, stages)
        if fill >= cfg.skip_fill and geometry.skew_deg(corners_s) <= cfg.skip_skew:
            return self._passthrough(rgb, timings, stages, found=False)

        corners = corners_s / scale  # về toạ độ ảnh gốc

        # 3) Corner refinement (sub-pixel)
        if cfg.corner_refine:
            t = time.perf_counter()
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            corners = geometry.refine_corners(gray, corners)
            timings["corner_refine"] = self._ms(t)
        if debug:
            vis = rgb.copy()
            cv2.polylines(vis, [geometry.order_points(corners).astype("int32")], True,
                          (0, 255, 0), 3)
            stages["corners"] = vis

        # 4) Perspective correction (loại nền: chỉ giữ pixel trong quad)
        t = time.perf_counter()
        out = geometry.four_point_transform(rgb, corners, cfg.margin)
        timings["perspective"] = self._ms(t)
        if debug:
            stages["warp"] = out.copy()

        # 5) Auto rotate (chuẩn hóa landscape nếu cấu hình)
        if cfg.rotate_landscape:
            out = geometry.auto_rotate_landscape(out)
        # 6) Deskew (sửa nghiêng nhỏ còn lại)
        if cfg.deskew:
            t = time.perf_counter()
            out = geometry.deskew(out)
            timings["deskew"] = self._ms(t)
        # 7) Adaptive padding
        if cfg.pad_ratio > 0:
            out = geometry.add_padding(out, cfg.pad_ratio)
        if debug:
            stages["padded"] = out.copy()

        # 8) Enhancement: CLAHE → Sharpen → Denoise
        t = time.perf_counter()
        if cfg.clahe:
            out = enhance.clahe(out)
        if cfg.sharpen:
            out = enhance.sharpen(out)
        if cfg.denoise:
            out = enhance.denoise(out)
        timings["enhance"] = self._ms(t)

        out = enhance.resize_cap(out, cfg.out_long)
        if debug:
            stages["output"] = out.copy()
        return RectifyResult(Image.fromarray(out), True,
                             corners=geometry.order_points(corners).tolist(),
                             timings=timings, stages=stages)

    # --- helpers ---
    def _passthrough(self, rgb, timings, stages, found=False) -> RectifyResult:
        out = enhance.resize_cap(rgb, self.cfg.out_long)
        if stages is not None and "output" not in stages and stages:
            stages["output"] = out.copy()
        return RectifyResult(Image.fromarray(out), found, timings=timings, stages=stages)

    @staticmethod
    def _ms(t: float) -> float:
        return round((time.perf_counter() - t) * 1000, 1)
