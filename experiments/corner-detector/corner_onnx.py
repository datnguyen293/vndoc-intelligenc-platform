"""Inference corner detector qua ONNX Runtime (CPU, offline) — KHÔNG cần ultralytics/torch.

Đây là bản dùng cho TÍCH HỢP service: chỉ onnxruntime (đã có sẵn trong bundle qua RapidOCR)
+ numpy + cv2. Tự làm tiền/hậu xử lý mà ultralytics vốn lo hộ:
  - letterbox ảnh về 640 (giữ tỉ lệ, pad 114),
  - giải output YOLOv8-pose [1, 17, 8400] (4 box + 1 conf + 4 keypoint×3),
  - map keypoint từ 640 về toạ độ ảnh gốc → 4 góc.
"""
from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort

from corner_rectify import order_points   # dùng chung logic sắp góc + warp


class CornerDetectorONNX:
    def __init__(self, onnx_path: str, imgsz: int = 640, conf: float = 0.25):
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        self.imgsz = imgsz
        self.conf = conf

    def _letterbox(self, bgr: np.ndarray):
        h, w = bgr.shape[:2]
        s = self.imgsz / max(h, w)
        nw, nh = min(self.imgsz, round(w * s)), min(self.imgsz, round(h * s))  # clamp tránh 641
        canvas = np.full((self.imgsz, self.imgsz, 3), 114, np.uint8)
        dw, dh = (self.imgsz - nw) // 2, (self.imgsz - nh) // 2
        canvas[dh:dh + nh, dw:dw + nw] = cv2.resize(bgr, (nw, nh))
        return canvas, s, dw, dh

    def corners(self, bgr: np.ndarray) -> np.ndarray | None:
        lb, s, dw, dh = self._letterbox(bgr)
        rgb = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = rgb.transpose(2, 0, 1)[None]                       # 1×3×640×640
        out = self.sess.run(None, {self.inp: blob})[0]           # [1, 17, 8400]
        pred = out[0].T                                          # [8400, 17]
        conf = pred[:, 4]
        keep = conf > self.conf
        if not keep.any():
            return None
        best = pred[keep][conf[keep].argmax()]                   # box tự tin nhất (1 thẻ)
        kpts = best[5:].reshape(4, 3)[:, :2]                     # 4×(x,y) trong 640
        pts = np.empty((4, 2), np.float32)
        pts[:, 0] = (kpts[:, 0] - dw) / s                        # bỏ pad + về ảnh gốc
        pts[:, 1] = (kpts[:, 1] - dh) / s
        if not np.isfinite(pts).all():
            return None
        return pts

    def rectify(self, bgr: np.ndarray, out_long: int = 1100, pad: float = 0.04) -> np.ndarray | None:
        pts = self.corners(bgr)
        if pts is None:
            return None
        rect = order_points(pts)
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
