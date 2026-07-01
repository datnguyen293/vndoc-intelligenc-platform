"""Fine-tune model góc trên SYNTH + REAL gộp (bước B).

Sau khi gán nhãn ảnh thật bằng label_corners.py → real_data/, chạy đây để fine-tune từ
best.pt (đã train trên synth). Gộp synth (nhiều) + real (ít nhưng thật) → tránh overfit
ảnh thật mà vẫn kéo model về đúng phân phối thật. LR thấp, ít epoch.

Chạy:  python finetune.py --weights runs/pose/weights/best.pt --synth data --real real_data
"""
from __future__ import annotations

import argparse
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


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
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(args.real, "images", "train")):
        raise SystemExit(f"Chưa có nhãn thật trong {args.real}/ — gán bằng label_corners.py trước.")

    data = _combined_yaml(args.synth, args.real)
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
