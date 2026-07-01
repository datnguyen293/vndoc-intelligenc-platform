"""Xuất model pose → ONNX (chạy CPU offline khi tích hợp vào rectifier).

Chạy:  python export.py --weights runs/pose/weights/best.pt
"""
from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="runs/pose/weights/best.pt")
    ap.add_argument("--imgsz", type=int, default=640)
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    path = model.export(format="onnx", imgsz=args.imgsz, opset=12, simplify=True, dynamic=False)
    print("ONNX:", path)


if __name__ == "__main__":
    main()
