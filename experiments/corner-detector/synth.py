"""Sinh dữ liệu TỔNG HỢP để train YOLOv8-pose detect 4 góc thẻ (nhánh thử nghiệm).

Ý tưởng (theo cơ chế các bài báo, nhưng tự sinh nhãn): lấy ảnh thẻ phẳng → biến đổi
PHỐI CẢNH ngẫu nhiên (nghiêng/xoay/scale) → ghép lên NỀN NHIỄU ngẫu nhiên (giả lập bàn,
bìa folder, vân gỗ...) + nhiễu quang học (sáng/mờ/loá/JPEG). Vì ta TỰ biến đổi nên biết
CHÍNH XÁC 4 góc trong ảnh kết quả → nhãn tự động, khỏi gán tay.

Xuất định dạng YOLOv8-pose: mỗi ảnh 1 instance = 1 bbox (bao thẻ) + 4 keypoint (góc theo
thứ tự TL, TR, BR, BL), toạ độ chuẩn hoá [0,1].

Chạy:  python -m synth --cards ../../service/samples --out data --n 4000
(cần: numpy, opencv-python, pillow — đã có trong venv service)
"""
from __future__ import annotations

import argparse
import glob
import os
import random

import cv2
import numpy as np

CANVAS = 640                    # ảnh train vuông 640 (YOLO)
KPT_ORDER = ("TL", "TR", "BR", "BL")


def _list_cards(root: str) -> list[str]:
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    files: list[str] = []
    for e in exts:
        files += glob.glob(os.path.join(root, "**", e), recursive=True)
    return sorted(files)


def _load_card(path: str) -> np.ndarray | None:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return None
    # Chuẩn hoá chiều rộng ~600 để nhất quán tốc độ warp.
    h, w = img.shape[:2]
    if w > 700:
        s = 700 / w
        img = cv2.resize(img, (int(w * s), int(h * s)))
    return img


# ------------------------- nền ngẫu nhiên -------------------------

def _random_background(rng: random.Random, cards: list[np.ndarray]) -> np.ndarray:
    """Nền: ~55% ẢNH THẬT (mẫu thẻ khác, làm MỜ NẶNG → xoá nhận dạng, giữ vân/ánh sáng
    thật) + ~45% thủ tục. Nền thật giúp thu hẹp khoảng cách synthetic-to-real (v2)."""
    if cards and rng.random() < 0.55:
        src = rng.choice(cards)
        h, w = src.shape[:2]
        cw, ch = rng.randint(w // 2, w), rng.randint(h // 2, h)
        x, y = rng.randint(0, max(1, w - cw)), rng.randint(0, max(1, h - ch))
        bg = cv2.resize(src[y:y + ch, x:x + cw], (CANVAS, CANVAS))
        k = rng.choice([21, 31, 41, 51])
        bg = cv2.GaussianBlur(bg, (k, k), 0)
        return np.clip(bg.astype(np.float32) * rng.uniform(0.6, 1.2) + rng.uniform(-20, 20),
                       0, 255).astype(np.uint8)
    return _proc_bg(rng)


def _proc_bg(rng: random.Random) -> np.ndarray:
    """Nền thủ tục: màu trơn, gradient, vân sọc, khối, hoặc nhiễu."""
    kind = rng.choice(["solid", "gradient", "stripes", "noise", "blocks"])
    base = np.zeros((CANVAS, CANVAS, 3), np.uint8)
    c1 = np.array([rng.randint(20, 200) for _ in range(3)], np.float32)
    c2 = np.array([rng.randint(20, 200) for _ in range(3)], np.float32)
    if kind == "solid":
        base[:] = c1
    elif kind == "gradient":
        t = np.linspace(0, 1, CANVAS, dtype=np.float32)[:, None, None]
        base[:] = (c1 * (1 - t) + c2 * t).astype(np.uint8)
    elif kind == "stripes":
        base[:] = c1
        step = rng.randint(12, 48)
        base[:, ::step] = c2
        if rng.random() < 0.5:
            base = cv2.rotate(base, cv2.ROTATE_90_CLOCKWISE)
    elif kind == "blocks":
        n = rng.randint(3, 8)
        for _ in range(n):
            x, y = rng.randint(0, CANVAS), rng.randint(0, CANVAS)
            w, h = rng.randint(60, 300), rng.randint(60, 300)
            col = tuple(rng.randint(20, 210) for _ in range(3))
            cv2.rectangle(base, (x, y), (x + w, y + h), col, -1)
    else:  # noise
        base[:] = c1
        noise = np.random.randint(0, 60, (CANVAS, CANVAS, 3), np.uint8)
        base = cv2.add(base, noise)
    if rng.random() < 0.5:
        k = rng.choice([3, 5, 7])
        base = cv2.GaussianBlur(base, (k, k), 0)
    return base


# ------------------------- biến đổi thẻ -------------------------

def _dst_quad(rng: random.Random, aspect: float) -> np.ndarray:
    """4 góc đích trên canvas theo TỈ LỆ ảnh nguồn (aspect = w/h) → thẻ DỌC lẫn NGANG (thẻ
    Đảng viên chip dọc, CCCD/CMND chụp dọc...). Jitter phối cảnh MẠNH + xoay RỘNG để bền với
    ảnh chụp góc chéo tự do của người dùng."""
    aspect = max(0.3, aspect * rng.uniform(0.9, 1.1))     # jitter nhẹ tỉ lệ
    fill = rng.uniform(0.30, 0.85)                         # cạnh DÀI chiếm bao nhiêu canvas
    long_px = CANVAS * fill
    if aspect >= 1.0:                                     # ngang: rộng là cạnh dài
        bw, bh = long_px, long_px / aspect
    else:                                                # dọc: cao là cạnh dài
        bh, bw = long_px, long_px * aspect
    cx = rng.uniform(bw / 2, CANVAS - bw / 2)
    cy = rng.uniform(bh / 2, CANVAS - bh / 2)
    base = np.array([
        [cx - bw / 2, cy - bh / 2],
        [cx + bw / 2, cy - bh / 2],
        [cx + bw / 2, cy + bh / 2],
        [cx - bw / 2, cy + bh / 2],
    ], np.float32)
    # phối cảnh mạnh hơn (±18% cạnh) → mô phỏng góc chụp chéo/foreshortening.
    jit = 0.18 * min(bw, bh)
    base += np.array([[rng.uniform(-jit, jit), rng.uniform(-jit, jit)] for _ in range(4)], np.float32)
    # xoay ±40° (rộng hơn) — giữ dưới ~45° để định danh keypoint theo vị trí còn ổn định;
    # xoay 90/180/270 vẫn để OrientingOcr lo ở khâu OCR.
    ang = rng.uniform(-40, 40)
    R = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
    ones = np.ones((4, 1), np.float32)
    base = (R @ np.hstack([base, ones]).T).T.astype(np.float32)
    return _fit_canvas(base)


def _fit_canvas(quad: np.ndarray, pad: int = 10) -> np.ndarray:
    """Đảm bảo 4 góc NẰM TRONG canvas [pad, CANVAS-pad] (scale xuống + dịch vào) — nếu không
    YOLO loại nhãn 'out of bounds' (toạ độ chuẩn hoá <0 hoặc >1)."""
    quad = quad.astype(np.float32).copy()
    w = quad[:, 0].max() - quad[:, 0].min()
    h = quad[:, 1].max() - quad[:, 1].min()
    s = min(1.0, (CANVAS - 2 * pad) / max(w, h, 1e-6))
    c = quad.mean(axis=0)
    quad = (quad - c) * s + c
    xmin, xmax = quad[:, 0].min(), quad[:, 0].max()
    ymin, ymax = quad[:, 1].min(), quad[:, 1].max()
    dx = (pad - xmin) if xmin < pad else ((CANVAS - pad) - xmax if xmax > CANVAS - pad else 0.0)
    dy = (pad - ymin) if ymin < pad else ((CANVAS - pad) - ymax if ymax > CANVAS - pad else 0.0)
    quad[:, 0] += dx
    quad[:, 1] += dy
    return quad


def _photometric(card: np.ndarray, rng: random.Random) -> np.ndarray:
    out = card.astype(np.float32)
    out = out * rng.uniform(0.6, 1.2) + rng.uniform(-25, 25)         # sáng/tương phản
    out = np.clip(out, 0, 255).astype(np.uint8)
    if rng.random() < 0.4:
        k = rng.choice([3, 5])
        out = cv2.GaussianBlur(out, (k, k), 0)
    return out


def _add_glare(canvas: np.ndarray, quad: np.ndarray, rng: random.Random) -> None:
    """Vệt loá trắng trên bề mặt thẻ (giả lập phản quang laminate)."""
    if rng.random() > 0.5:
        return
    cx, cy = quad.mean(axis=0)
    overlay = canvas.copy()
    axes = (rng.randint(40, 160), rng.randint(15, 60))
    cv2.ellipse(overlay, (int(cx), int(cy)), axes, rng.randint(0, 180), 0, 360, (255, 255, 255), -1)
    a = rng.uniform(0.15, 0.5)
    cv2.addWeighted(overlay, a, canvas, 1 - a, 0, canvas)


def _draw_sleeve(bg: np.ndarray, quad: np.ndarray, rng: random.Random) -> None:
    """Mô phỏng BAO NHỰA lanyard: vùng sáng đục TO HƠN thẻ quanh mép. Nhãn vẫn là góc THẺ
    bên trong → model học BỎ QUA bao, chỉ lấy góc thẻ (đúng ca sĩ quan v1 bị bám sai)."""
    if rng.random() > 0.5:
        return
    c = quad.mean(axis=0)
    exp = ((quad - c) * rng.uniform(1.06, 1.22) + c).astype(np.int32)
    color = tuple(int(rng.randint(190, 255)) for _ in range(3))
    overlay = bg.copy()
    cv2.fillConvexPoly(overlay, exp, color)
    a = rng.uniform(0.45, 0.8)
    cv2.addWeighted(overlay, a, bg, 1 - a, 0, bg)


def _scene_aug(canvas: np.ndarray, rng: random.Random) -> None:
    """Augment cảnh: bóng, color jitter (HSV), vignette, motion blur."""
    if rng.random() < 0.4:                                   # bóng
        ov = canvas.copy()
        cv2.circle(ov, (rng.randint(0, CANVAS), rng.randint(0, CANVAS)),
                   rng.randint(120, 360), (0, 0, 0), -1)
        a = rng.uniform(0.1, 0.35)
        cv2.addWeighted(ov, a, canvas, 1 - a, 0, canvas)
    if rng.random() < 0.6:                                   # color jitter HSV
        hsv = cv2.cvtColor(canvas, cv2.COLOR_BGR2HSV).astype(np.int16)
        hsv[..., 0] = (hsv[..., 0] + rng.randint(-8, 8)) % 180
        hsv[..., 1] = np.clip(hsv[..., 1] * rng.uniform(0.7, 1.3), 0, 255)
        hsv[..., 2] = np.clip(hsv[..., 2] * rng.uniform(0.7, 1.2), 0, 255)
        canvas[:] = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if rng.random() < 0.4:                                   # vignette
        yy, xx = np.ogrid[:CANVAS, :CANVAS]
        r = np.sqrt((xx - CANVAS / 2) ** 2 + (yy - CANVAS / 2) ** 2) / (CANVAS / 1.4)
        v = np.clip(1 - rng.uniform(0.3, 0.7) * r, 0.3, 1)[:, :, None]
        canvas[:] = np.clip(canvas.astype(np.float32) * v, 0, 255).astype(np.uint8)
    if rng.random() < 0.25:                                  # motion blur
        k = rng.choice([7, 9, 11])
        kern = np.zeros((k, k), np.float32)
        if rng.random() < 0.5:
            kern[k // 2, :] = 1
        else:
            kern[:, k // 2] = 1
        canvas[:] = cv2.filter2D(canvas, -1, kern / k)


def _compose(card: np.ndarray, rng: random.Random,
             cards: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Trả (ảnh canvas, quad 4 góc TL,TR,BR,BL). v2: nền thật + bao nhựa + scene aug."""
    h, w = card.shape[:2]
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
    dst = _dst_quad(rng, w / h)                       # theo tỉ lệ ảnh nguồn → dọc/ngang
    H = cv2.getPerspectiveTransform(src, dst)

    card = _photometric(card, rng)
    warped = cv2.warpPerspective(card, H, (CANVAS, CANVAS), borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), H, (CANVAS, CANVAS))

    bg = _random_background(rng, cards)
    _draw_sleeve(bg, dst, rng)                       # bao nhựa: trên nền, dưới thẻ
    m3 = (mask > 127)[:, :, None]
    canvas = np.where(m3, warped, bg).astype(np.uint8)
    _add_glare(canvas, dst, rng)
    _scene_aug(canvas, rng)
    if rng.random() < 0.6:                           # nén JPEG như ảnh chụp
        q = rng.randint(40, 92)
        ok, enc = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, q])
        if ok:
            canvas = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return canvas, dst


# ------------------------- nhãn YOLO-pose -------------------------

def _label(quad: np.ndarray) -> str:
    xs, ys = quad[:, 0], quad[:, 1]
    x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
    cx, cy = (x1 + x2) / 2 / CANVAS, (y1 + y2) / 2 / CANVAS
    bw, bh = (x2 - x1) / CANVAS, (y2 - y1) / CANVAS
    parts = ["0", f"{cx:.6f}", f"{cy:.6f}", f"{bw:.6f}", f"{bh:.6f}"]
    for (px, py) in quad:                            # 4 keypoint (chuẩn hoá) + visible=2
        parts += [f"{px / CANVAS:.6f}", f"{py / CANVAS:.6f}", "2"]
    return " ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True, help="thư mục ảnh thẻ phẳng (nguồn)")
    ap.add_argument("--out", default="data", help="thư mục xuất dataset YOLO")
    ap.add_argument("--n", type=int, default=4000, help="số ảnh sinh")
    ap.add_argument("--val", type=float, default=0.1, help="tỉ lệ val")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    cards = [c for c in (_load_card(p) for p in _list_cards(args.cards)) if c is not None]
    if not cards:
        raise SystemExit(f"Không có ảnh thẻ trong {args.cards}")
    print(f"Nguồn: {len(cards)} ảnh thẻ")

    for split in ("train", "val"):
        os.makedirs(os.path.join(args.out, "images", split), exist_ok=True)
        os.makedirs(os.path.join(args.out, "labels", split), exist_ok=True)

    n_val = int(args.n * args.val)
    for i in range(args.n):
        split = "val" if i < n_val else "train"
        card = rng.choice(cards)
        canvas, quad = _compose(card, rng, cards)
        stem = f"{i:06d}"
        cv2.imwrite(os.path.join(args.out, "images", split, stem + ".jpg"), canvas)
        with open(os.path.join(args.out, "labels", split, stem + ".txt"), "w") as f:
            f.write(_label(quad) + "\n")
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{args.n}")

    # data.yaml cho YOLOv8-pose (1 class 'card', 4 keypoint)
    yaml = (
        f"path: {os.path.abspath(args.out)}\n"
        "train: images/train\nval: images/val\n"
        "kpt_shape: [4, 3]\n"                       # 4 điểm, mỗi điểm (x,y,visible)
        "flip_idx: [1, 0, 3, 2]\n"                  # lật ngang: TL<->TR, BL<->BR
        "names:\n  0: card\n"
    )
    with open(os.path.join(args.out, "data.yaml"), "w") as f:
        f.write(yaml)
    print(f"Xong: {args.n} ảnh → {args.out}  (data.yaml đã ghi)")


if __name__ == "__main__":
    main()
