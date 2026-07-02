"""Corner-detector FALLBACK (thử nghiệm) — nắn thẻ bằng model 4 góc (ONNX) khi thẻ NHỎ trên
nền (ca classic hay hỏng). Chạy CPU qua onnxruntime (đã có sẵn), KHÔNG cần ultralytics/torch.

Chốt từ đánh giá golden: corner THAY THẾ classic thì kém (golden = output classic + ảnh đã
lấp khung). Nên chỉ dùng corner khi thẻ chiếm ÍT khung (nền nhiều để cắt) → thẻ lấp khung
vẫn để classic. Mặc định TẮT (DIP_RECTIFY_CORNER_FALLBACK).
"""
from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

log = logging.getLogger("dip.cv.corner")


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Sắp 4 góc về [TL, TR, BR, BL] BỀN với mọi góc xoay.

    Heuristic sum/diff cũ SẬP khi thẻ nghiêng ~45°: argmax(sum) và argmax(diff) trỏ cùng
    một đỉnh → br≡bl, một góc thật bị bỏ → tứ giác suy biến → warp ra ảnh trống → OCR mất
    chữ. Thay bằng sắp theo GÓC PHƯƠNG VỊ quanh tâm: argsort(atan2) tăng dần cho thứ tự
    chiều kim đồng hồ trên chu vi (y hướng xuống), KHÔNG bao giờ trùng đỉnh; xoay để bắt
    đầu ở đỉnh 'trên-trái' nhất (min x+y). Hướng cuối (0/90/180/270) do auto-orient lo.
    """
    pts = np.asarray(pts, dtype="float32")
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    pts = pts[np.argsort(ang)]
    start = int(np.argmin(pts.sum(axis=1)))
    return np.roll(pts, -start, axis=0).astype("float32")


def _quad_area(pts: np.ndarray) -> float:
    x, y = pts[:, 0], pts[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


class CornerModel:
    """Inference YOLOv8-pose 4 góc qua onnxruntime (letterbox 640 + giải [1,17,8400])."""

    def __init__(self, onnx_path: Any, imgsz: int = 640, conf: float = 0.30):
        import onnxruntime as ort
        self.sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        self.imgsz = imgsz
        self.conf = conf

    def corners(self, bgr: np.ndarray) -> np.ndarray | None:
        h, w = bgr.shape[:2]
        s = self.imgsz / max(h, w)
        nw, nh = min(self.imgsz, round(w * s)), min(self.imgsz, round(h * s))
        canvas = np.full((self.imgsz, self.imgsz, 3), 114, np.uint8)
        dw, dh = (self.imgsz - nw) // 2, (self.imgsz - nh) // 2
        canvas[dh:dh + nh, dw:dw + nw] = cv2.resize(bgr, (nw, nh))
        blob = (cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        out = self.sess.run(None, {self.inp: blob})[0]      # [1,17,8400]
        pred = out[0].T
        keep = pred[:, 4] > self.conf
        if not keep.any():
            return None
        best = pred[keep][pred[keep][:, 4].argmax()]
        kpts = best[5:].reshape(4, 3)[:, :2]
        pts = np.empty((4, 2), np.float32)
        pts[:, 0] = (kpts[:, 0] - dw) / s
        pts[:, 1] = (kpts[:, 1] - dh) / s
        return pts if np.isfinite(pts).all() else None

    def rectify(self, bgr: np.ndarray, out_long: int = 1100, pad: float = 0.04) -> np.ndarray | None:
        pts = self.corners(bgr)
        if pts is None:
            return None
        rect = _order_points(pts)
        if pad > 0:
            c = rect.mean(axis=0)
            rect = ((rect - c) * (1.0 + pad) + c).astype("float32")
        tl, tr, br, bl = rect
        w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
        h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
        if min(w, h) < 10:
            return None
        sc = out_long / max(w, h)
        W, H = int(round(w * sc)), int(round(h * sc))
        dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], np.float32)
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(bgr, M, (W, H))


class CornerAssistRectifier:
    """Bọc rectifier classic: nếu thẻ chiếm ÍT khung (< max_ratio) thì nắn bằng corner model;
    ngược lại (lấp khung / không detect) → dùng classic."""

    def __init__(self, classic: Any, model: CornerModel, max_ratio: float = 0.55):
        self._classic = classic
        self._model = model
        self._max_ratio = max_ratio

    def rectify(self, image: Any, polygon: Any):
        from PIL import Image
        try:
            bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
            pts = self._model.corners(bgr)
            if pts is not None:
                ratio = _quad_area(pts) / (bgr.shape[0] * bgr.shape[1])
                if ratio < self._max_ratio:                   # thẻ nhỏ trên nền → corner
                    warped = self._model.rectify(bgr)
                    if warped is not None:
                        log.info("corner fallback: thẻ chiếm %.0f%% khung → nắn bằng model góc", ratio * 100)
                        return Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
        except Exception as exc:  # noqa: BLE001 — lỗi corner KHÔNG được phá pipeline
            log.warning("corner fallback lỗi (%s) → dùng classic", exc)
        return self._classic.rectify(image, polygon)
