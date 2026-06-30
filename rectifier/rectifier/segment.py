"""Segmenter: tách vùng tài liệu khỏi nền → mask. 2 backend: classic (OpenCV) + YOLO.

Mask là ảnh nhị phân (uint8 0/255) cùng kích thước ảnh vào; vùng tài liệu = 255.
Backend `classic` chạy hoàn toàn offline, không cần model. Backend `yolo` tùy chọn,
nạp lazy và cần file weights cục bộ (không tải mạng).
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

import cv2
import numpy as np

log = logging.getLogger("rectifier.segment")


class Segmenter(Protocol):
    def segment(self, rgb: np.ndarray) -> np.ndarray | None:
        """Trả mask (uint8 0/255) của vùng tài liệu lớn nhất, hoặc None."""
        ...


class ClassicSegmenter:
    """OpenCV thuần, 2 tầng (offline, không cần model):

    1. *Rẻ & nhanh*: Otsu (2 chiều) + Canny + morphology → thành phần lớn nhất.
       Tốt khi tài liệu tương phản rõ với nền (vd nền tối / nền trơn).
    2. *Fallback GrabCut*: khi tầng 1 cho mask yếu (diện tích nhỏ hoặc không ra tứ giác),
       chạy GrabCut khởi tạo bằng hình chữ nhật tâm ảnh — bám sát mép tài liệu trong các
       ca tương phản thấp (vd thẻ kem trên bàn gỗ). Chỉ trả phí GrabCut khi cần.
    """

    def __init__(self, min_area_ratio: float = 0.2, grabcut_fallback: bool = True,
                 strong_rect: float = 0.90, gc_work: int = 320) -> None:
        self.min_area_ratio = min_area_ratio
        self.grabcut_fallback = grabcut_fallback
        self.strong_rect = strong_rect   # tầng 1 đạt độ-chữ-nhật này → bỏ qua GrabCut
        self.gc_work = gc_work           # độ phân giải chạy GrabCut (giữ nhanh)

    def segment(self, rgb: np.ndarray) -> np.ndarray | None:
        area_img = rgb.shape[0] * rgb.shape[1]
        cheap = self._cheap(rgb)
        # tầng 1 không thấy "chủ thể" tách khỏi nền (vd tài liệu lấp kín khung)
        # → trả None để core giữ nguyên ảnh, KHÔNG dùng GrabCut bịa ra vùng.
        if cheap is None:
            return None
        cheap_rect = self._rectangularity(cheap)
        # tầng 1 đã ra hình chữ nhật rõ → dùng luôn (đường nhanh).
        if not self.grabcut_fallback or cheap_rect >= self.strong_rect:
            return cheap
        # tầng 1 yếu (méo/tràn nền) → GrabCut tinh chỉnh; chọn mask "chữ-nhật" hơn.
        gc = self._grabcut(rgb)
        gc_rect = self._rectangularity(gc) if self._area_ok(gc, area_img) else 0.0
        cheap_score = cheap_rect if self._area_ok(cheap, area_img) else 0.0
        return gc if gc_rect > cheap_score else cheap

    # --- tầng 1: ngưỡng + cạnh (nhanh) ---
    def _cheap(self, rgb: np.ndarray) -> np.ndarray | None:
        gray = cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (5, 5), 0)
        area_img = rgb.shape[0] * rgb.shape[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))

        best, best_area = None, 0.0
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        edges = cv2.morphologyEx(cv2.Canny(gray, 50, 150), cv2.MORPH_CLOSE, kernel)
        for binary in (otsu, cv2.bitwise_not(otsu), edges):
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                a = cv2.contourArea(c)
                # bỏ vùng ~cả ảnh (nền) và vùng quá nhỏ
                if self.min_area_ratio * area_img <= a <= 0.985 * area_img and a > best_area:
                    best, best_area = c, a
        if best is None:
            return None
        mask = np.zeros(gray.shape, dtype="uint8")
        cv2.drawContours(mask, [cv2.convexHull(best)], -1, 255, thickness=cv2.FILLED)
        return mask

    # --- tầng 2: GrabCut từ chữ nhật tâm ảnh (chạy ở độ phân giải nhỏ cho nhanh) ---
    def _grabcut(self, rgb: np.ndarray) -> np.ndarray | None:
        h, w = rgb.shape[:2]
        scale = self.gc_work / max(h, w) if max(h, w) > self.gc_work else 1.0
        small = cv2.resize(rgb, (int(w * scale), int(h * scale))) if scale < 1 else rgb
        sh, sw = small.shape[:2]
        bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
        mask = np.zeros((sh, sw), np.uint8)
        rect = (int(0.06 * sw), int(0.06 * sh), int(0.88 * sw), int(0.88 * sh))
        try:
            cv2.grabCut(bgr, mask, rect, np.zeros((1, 65), np.float64),
                        np.zeros((1, 65), np.float64), 3, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            return None
        fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
        if scale < 1:  # upscale mask về kích thước ảnh vào
            fg = cv2.resize(fg, (w, h), interpolation=cv2.INTER_NEAREST)
        cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        out = np.zeros((h, w), np.uint8)
        cv2.drawContours(out, [cv2.convexHull(max(cnts, key=cv2.contourArea))], -1, 255,
                         thickness=cv2.FILLED)
        return out

    def _area_ok(self, mask: np.ndarray | None, area_img: int) -> bool:
        """Diện tích vùng lớn nhất nằm trong [min_area_ratio, 0.985] của ảnh."""
        if mask is None:
            return False
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return False
        a = cv2.contourArea(max(cnts, key=cv2.contourArea))
        return self.min_area_ratio * area_img <= a <= 0.985 * area_img

    @staticmethod
    def _rectangularity(mask: np.ndarray | None) -> float:
        """Độ "chữ-nhật" = diện tích contour / diện tích minAreaRect bao nó (0..1)."""
        if mask is None:
            return 0.0
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return 0.0
        c = max(cnts, key=cv2.contourArea)
        (_, (bw, bh), _) = cv2.minAreaRect(c)
        return float(cv2.contourArea(c) / max(1.0, bw * bh))


class YoloSegmenter:
    """YOLO segmentation (ultralytics). Lazy import; cần weights cục bộ.

    Đặt đường dẫn file .pt vào cấu hình `yolo_weights`. Không tải mạng khi chạy.
    """

    def __init__(self, weights: str, conf: float = 0.25) -> None:
        from ultralytics import YOLO  # lazy: chỉ nạp khi dùng backend yolo

        self._model = YOLO(weights)
        self.conf = conf
        log.info("YOLO segmenter sẵn sàng: %s", weights)

    def segment(self, rgb: np.ndarray) -> np.ndarray | None:
        res = self._model.predict(rgb, conf=self.conf, verbose=False)
        if not res or res[0].masks is None or len(res[0].masks) == 0:
            return None
        h, w = rgb.shape[:2]
        # chọn mask có diện tích lớn nhất
        masks = res[0].masks.data.cpu().numpy()  # (n, mh, mw) 0..1
        best = max(masks, key=lambda m: float(m.sum()))
        m = cv2.resize((best > 0.5).astype("uint8") * 255, (w, h),
                       interpolation=cv2.INTER_NEAREST)
        return m


def get_segmenter(name: str, yolo_weights: str | None, min_area_ratio: float,
                  grabcut_fallback: bool = True) -> Any:
    """Tạo segmenter theo cấu hình; YOLO lỗi/thiếu weights → fallback classic."""
    if name == "yolo" and yolo_weights:
        try:
            return YoloSegmenter(yolo_weights)
        except Exception as exc:  # noqa: BLE001
            log.warning("YOLO segmenter không dùng được (%s) → classic", exc)
    return ClassicSegmenter(min_area_ratio=min_area_ratio,
                            grabcut_fallback=grabcut_fallback)
