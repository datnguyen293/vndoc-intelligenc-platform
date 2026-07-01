"""Inference detect 4 góc + nắn phối cảnh (nhánh thử nghiệm).

Dùng model YOLOv8-pose đã train → 4 keypoint góc → order_points → warp phối cảnh về thẻ
thẳng. Đánh giá bằng ultralytics (torch) cho nhanh; khi TÍCH HỢP thật sẽ chuyển sang
onnxruntime (CPU, offline) để khỏi kéo ultralytics vào service.
"""
from __future__ import annotations

import cv2
import numpy as np


def order_points(pts: np.ndarray) -> np.ndarray:
    """Sắp 4 điểm → TL, TR, BR, BL (theo tổng/hiệu toạ độ) — GIỐNG rectifier/geometry."""
    pts = np.asarray(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]
    rect[3] = pts[np.argmax(d)]
    return rect


class CornerRectifier:
    def __init__(self, weights: str, conf: float = 0.25, device: str = "cpu"):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.conf = conf
        self.device = device       # CPU: tránh tranh GPU với training + khớp mục tiêu CPU

    def corners(self, bgr: np.ndarray) -> np.ndarray | None:
        """Trả 4 góc (float32, toạ độ ảnh gốc) của box tự-tin nhất, hoặc None."""
        res = self.model(bgr, conf=self.conf, device=self.device, verbose=False)[0]
        if res.keypoints is None or res.keypoints.xy is None or len(res.keypoints.xy) == 0:
            return None
        # chọn instance conf cao nhất
        if res.boxes is not None and len(res.boxes) > 1:
            i = int(res.boxes.conf.argmax().item())
        else:
            i = 0
        kpts = res.keypoints.xy[i].cpu().numpy().astype("float32")  # (4,2)
        if kpts.shape != (4, 2) or not np.isfinite(kpts).all():
            return None
        return kpts

    def rectify(self, bgr: np.ndarray, out_long: int = 1100, pad: float = 0.04) -> np.ndarray | None:
        """Nắn thẻ về ảnh thẳng dựa 4 góc. `pad`: nới 4 góc ra ngoài (%) để không cắt mất
        chữ sát mép (vd 'Hạn sử dụng' ở góc). None nếu không detect được."""
        pts = self.corners(bgr)
        if pts is None:
            return None
        rect = order_points(pts)
        if pad > 0:                                   # nới ra ngoài quanh tâm
            c = rect.mean(axis=0)
            rect = ((rect - c) * (1.0 + pad) + c).astype("float32")
        tl, tr, br, bl = rect
        w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
        h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
        if min(w, h) < 10:
            return None
        # giữ tỉ lệ, cạnh dài = out_long
        scale = out_long / max(w, h)
        W, H = int(round(w * scale)), int(round(h * scale))
        dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(bgr, M, (W, H))

    def draw(self, bgr: np.ndarray) -> np.ndarray:
        """Vẽ 4 góc + khung lên ảnh (để kiểm tra trực quan)."""
        out = bgr.copy()
        pts = self.corners(bgr)
        if pts is None:
            cv2.putText(out, "NO CARD", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            return out
        rect = order_points(pts)
        cols = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255)]  # TL,TR,BR,BL
        for (x, y), c in zip(rect, cols):
            cv2.circle(out, (int(x), int(y)), 10, c, -1)
        for i in range(4):
            cv2.line(out, tuple(rect[i].astype(int)), tuple(rect[(i + 1) % 4].astype(int)), (255, 255, 255), 3)
        return out
