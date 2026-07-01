"""Fine-tune model góc trên SYNTH + REAL gộp (bước B).

Sau khi gán nhãn ảnh thật bằng label_corners.py → real_data/, chạy đây để fine-tune từ
best.pt (đã train trên synth). Gộp synth (nhiều) + real (ít nhưng thật) → tránh overfit
ảnh thật mà vẫn kéo model về đúng phân phối thật. LR thấp, ít epoch.

Chạy:  python finetune.py --weights runs/pose/weights/best.pt --synth data --real real_data
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))


def _oversample_real(real: str, target_ratio: float, n_synth: int) -> str:
    """Nhân bản ảnh thật (train) ~target_ratio so với synth → real đủ 'nặng' để fine-tune
    kéo model về phân phối thật (34 ảnh/7200 synth = 0.5% thì quá loãng). Val giữ nguyên."""
    reals = sorted(glob.glob(os.path.join(real, "images", "train", "*")))
    n = len(reals)
    if n == 0:
        raise SystemExit("real_data/images/train rỗng")
    repeat = max(1, round(target_ratio * n_synth / max(1, n * (1 - target_ratio))))
    out = os.path.join(_HERE, "real_oversampled")
    if os.path.exists(out):
        shutil.rmtree(out)
    for split in ("train", "val"):
        os.makedirs(os.path.join(out, "images", split), exist_ok=True)
        os.makedirs(os.path.join(out, "labels", split), exist_ok=True)
    # val: copy nguyên
    for ip in glob.glob(os.path.join(real, "images", "val", "*")):
        stem = os.path.splitext(os.path.basename(ip))[0]
        shutil.copy(ip, os.path.join(out, "images", "val", os.path.basename(ip)))
        shutil.copy(os.path.join(real, "labels", "val", stem + ".txt"),
                    os.path.join(out, "labels", "val", stem + ".txt"))
    # train: nhân bản ×repeat
    for ip in reals:
        stem = os.path.splitext(os.path.basename(ip))[0]
        ext = os.path.splitext(ip)[1]
        lp = os.path.join(real, "labels", "train", stem + ".txt")
        for k in range(repeat):
            shutil.copy(ip, os.path.join(out, "images", "train", f"{stem}_{k}{ext}"))
            shutil.copy(lp, os.path.join(out, "labels", "train", f"{stem}_{k}.txt"))
    print(f"Oversample real: {n} ảnh ×{repeat} = {n * repeat} (mục tiêu ~{target_ratio:.0%} mix)")
    return out


def _combined_yaml(synth: str, real: str) -> str:
    s, r = os.path.abspath(synth), os.path.abspath(real)
    path = os.path.join(_HERE, "combined_data.yaml")
    with open(path, "w") as f:
        f.write(
            "train:\n"
            f"  - {os.path.join(s, 'images', 'train')}\n"
            f"  - {os.path.join(r, 'images', 'train')}\n"
            "val:\n"
            f"  - {os.path.join(s, 'images', 'val')}\n"
            f"  - {os.path.join(r, 'images', 'val')}\n"
            "kpt_shape: [4, 3]\nflip_idx: [1, 0, 3, 2]\nnames:\n  0: card\n"
        )
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="runs/pose/weights/best.pt")
    ap.add_argument("--synth", default="data")
    ap.add_argument("--real", default="real_data")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="0")
    ap.add_argument("--ratio", type=float, default=0.15, help="tỉ lệ ảnh thật trong mix train")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(args.real, "images", "train")):
        raise SystemExit(f"Chưa có nhãn thật trong {args.real}/ — gán bằng label_corners.py trước.")

    n_synth = len(glob.glob(os.path.join(args.synth, "images", "train", "*")))
    real_os = _oversample_real(args.real, args.ratio, n_synth)
    data = _combined_yaml(args.synth, real_os)
    from ultralytics import YOLO

    model = YOLO(args.weights)
    model.train(
        data=data, epochs=args.epochs, imgsz=640, batch=args.batch, device=args.device,
        project=os.path.join(_HERE, "runs"), name="finetune", exist_ok=True,
        lr0=0.003,                              # LR thấp cho fine-tune
        fliplr=0.0, flipud=0.0, mosaic=0.0, degrees=0.0, perspective=0.0,
        hsv_h=0.015, hsv_s=0.5, hsv_v=0.4,
    )
    print("Fine-tune xong → runs/finetune/weights/best.pt")


if __name__ == "__main__":
    main()
