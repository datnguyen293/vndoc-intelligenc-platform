"""Công cụ ĐÁNH DẤU 4 GÓC thẻ trên ảnh THẬT → nhãn YOLO-pose để fine-tune model (bước B).

GUI Tkinter (khỏi cần cv2 highgui). Với mỗi ảnh: bấm CHUỘT TRÁI vào 4 góc thẻ (thứ tự
gợi ý: Trên-trái → Trên-phải → Dưới-phải → Dưới-trái, theo chiều kim đồng hồ). Tool tự
chuẩn hoá thứ tự (order_points) nên bấm hơi lệch thứ tự vẫn được.

Phím: [S/Enter]=lưu & ảnh kế · [U]=undo điểm cuối · [R]=xoá hết điểm · [N/Space]=bỏ qua ·
      [Q/Esc]=thoát. Ảnh đã gán (có nhãn) sẽ tự bỏ qua khi mở lại → gán theo đợt được.

Chạy:
    python label_corners.py --images real_images --out real_data
Bỏ ảnh vào thư mục real_images/ trước (jpg/png). Nhãn ra real_data/{images,labels}/{train,val}.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

MAX_W, MAX_H = 1100, 780     # cửa sổ hiển thị tối đa (ảnh lớn sẽ thu nhỏ để vừa màn hình)
COLORS = ["#ff3030", "#30ff30", "#3030ff", "#ffff30"]   # TL, TR, BR, BL


def order_points(pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]     # TL
    rect[2] = pts[np.argmax(s)]     # BR
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]     # TR
    rect[3] = pts[np.argmax(d)]     # BL
    return rect


def yolo_pose_label(quad: np.ndarray, w: int, h: int) -> str:
    rect = order_points(quad)
    xs, ys = rect[:, 0], rect[:, 1]
    x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
    cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
    bw, bh = (x2 - x1) / w, (y2 - y1) / h
    parts = ["0", f"{cx:.6f}", f"{cy:.6f}", f"{bw:.6f}", f"{bh:.6f}"]
    for (px, py) in rect:
        parts += [f"{px / w:.6f}", f"{py / h:.6f}", "2"]
    return " ".join(parts)


class Labeler:
    def __init__(self, root: tk.Tk, images: list[str], out: str, val_ratio: float):
        self.root = root
        self.images = images
        self.out = out
        self.val_ratio = val_ratio
        self.idx = -1
        self.pts: list[tuple[float, float]] = []      # toạ độ GỐC
        self.scale = 1.0

        self.canvas = tk.Canvas(root, bg="gray20", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.status = tk.Label(root, anchor="w", font=("Segoe UI", 11), bg="black", fg="white")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.bind("<Button-1>", self.on_click)
        for k in ("s", "S", "Return"):
            root.bind(f"<{k}>", lambda e: self.save())
        root.bind("<u>", lambda e: self.undo())
        root.bind("<U>", lambda e: self.undo())
        root.bind("<r>", lambda e: self.reset())
        root.bind("<R>", lambda e: self.reset())
        for k in ("n", "N", "space"):
            root.bind(f"<{k}>", lambda e: self.next_img(save=False))
        for k in ("q", "Q", "Escape"):
            root.bind(f"<{k}>", lambda e: root.destroy())

        self.next_img(save=False)

    # --- điều hướng ---
    def _label_path(self, img_path: str, split: str) -> str:
        stem = os.path.splitext(os.path.basename(img_path))[0]
        return os.path.join(self.out, "labels", split, stem + ".txt")

    def _already(self, img_path: str) -> bool:
        return any(os.path.exists(self._label_path(img_path, s)) for s in ("train", "val"))

    def next_img(self, save: bool):
        self.idx += 1
        while self.idx < len(self.images) and self._already(self.images[self.idx]):
            self.idx += 1
        if self.idx >= len(self.images):
            self.status.config(text="XONG — đã gán hết ảnh. Nhấn Q để thoát.")
            return
        self.pts = []
        path = self.images[self.idx]
        self.pil = Image.open(path).convert("RGB")
        w, h = self.pil.size
        self.scale = min(1.0, MAX_W / w, MAX_H / h)
        dw, dh = int(w * self.scale), int(h * self.scale)
        self.tkimg = ImageTk.PhotoImage(self.pil.resize((dw, dh)))
        self.canvas.config(width=dw, height=dh)
        self.redraw()

    # --- tương tác ---
    def on_click(self, e):
        if len(self.pts) >= 4:
            return
        self.pts.append((e.x / self.scale, e.y / self.scale))
        self.redraw()

    def undo(self):
        if self.pts:
            self.pts.pop()
            self.redraw()

    def reset(self):
        self.pts = []
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg)
        disp = [(x * self.scale, y * self.scale) for x, y in self.pts]
        for i in range(len(disp)):
            if i > 0:
                self.canvas.create_line(*disp[i - 1], *disp[i], fill="white", width=2)
        if len(disp) == 4:
            self.canvas.create_line(*disp[3], *disp[0], fill="white", width=2)
        for i, (x, y) in enumerate(disp):
            self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=COLORS[i], outline="white")
        n = len(self.pts)
        left = len(self.images) - self.idx
        hint = ["Trên-trái", "Trên-phải", "Dưới-phải", "Dưới-trái"]
        tip = f"→ bấm góc: {hint[n]}" if n < 4 else "ĐỦ 4 góc — nhấn S để LƯU"
        self.status.config(
            text=f"[{self.idx + 1}/{len(self.images)}] {os.path.basename(self.images[self.idx])}  "
                 f"|  điểm: {n}/4  {tip}   |  S=lưu U=undo R=xoá N=bỏ qua Q=thoát"
        )

    def save(self):
        if len(self.pts) != 4:
            self.status.config(text="Cần đủ 4 góc mới lưu được (đang %d)." % len(self.pts))
            return
        path = self.images[self.idx]
        w, h = self.pil.size
        # cứ ~1/6 cho val
        split = "val" if (self.idx % 6 == 5) else "train"
        os.makedirs(os.path.join(self.out, "images", split), exist_ok=True)
        os.makedirs(os.path.join(self.out, "labels", split), exist_ok=True)
        stem = os.path.splitext(os.path.basename(path))[0]
        shutil.copy(path, os.path.join(self.out, "images", split, os.path.basename(path)))
        with open(os.path.join(self.out, "labels", split, stem + ".txt"), "w") as f:
            f.write(yolo_pose_label(np.array(self.pts, dtype="float32"), w, h) + "\n")
        self.next_img(save=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="real_images", help="thư mục ảnh THẬT cần gán")
    ap.add_argument("--out", default="real_data", help="thư mục dataset YOLO xuất ra")
    ap.add_argument("--val", type=float, default=0.17)
    args = ap.parse_args()

    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    imgs = sorted(p for e in exts for p in glob.glob(os.path.join(args.images, "**", e), recursive=True))
    if not imgs:
        raise SystemExit(f"Không có ảnh trong {args.images}/ — bỏ ảnh vào đó rồi chạy lại.")

    # data.yaml (giống synth) để train/fine-tune
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "data.yaml"), "w") as f:
        f.write(
            f"path: {os.path.abspath(args.out)}\n"
            "train: images/train\nval: images/val\n"
            "kpt_shape: [4, 3]\nflip_idx: [1, 0, 3, 2]\nnames:\n  0: card\n"
        )

    root = tk.Tk()
    root.title("VNDoc — đánh dấu 4 góc thẻ")
    Labeler(root, imgs, args.out, args.val)
    root.mainloop()
    print("Đã lưu nhãn vào", args.out)


if __name__ == "__main__":
    main()
