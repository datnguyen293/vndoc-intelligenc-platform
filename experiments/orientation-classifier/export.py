"""Xuất orientation-classifier sang ONNX (chạy onnxruntime CPU khi tích hợp).

Nhúng meta: thứ tự lớp (để map argmax → độ xoay) + imgsz, đọc lại lúc infer.
Chạy:  PY=../../build/stage/runtime/python.exe ; $PY export.py --weights runs/best.pt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(HERE / "runs" / "best.pt"))
    ap.add_argument("--out", default=str(HERE / "runs" / "orientation.onnx"))
    args = ap.parse_args()

    ckpt = torch.load(args.weights, map_location="cpu", weights_only=False)
    classes = ckpt["classes"]
    imgsz = ckpt.get("imgsz", 160)
    m = mobilenet_v3_small()
    m.classifier[3] = nn.Linear(m.classifier[3].in_features, 4)
    m.load_state_dict(ckpt["state_dict"])
    m.eval()

    dummy = torch.zeros(1, 3, imgsz, imgsz)
    torch.onnx.export(
        m, dummy, args.out, input_names=["input"], output_names=["logits"],
        opset_version=13, dynamic_axes={"input": {0: "b"}, "logits": {0: "b"}},
    )
    # meta cạnh file onnx: map index lớp → độ xoay CCW về upright, và imgsz.
    meta = {"classes": classes, "imgsz": imgsz,
            "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}
    Path(args.out).with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"XONG ONNX: {args.out}  (classes={classes}, imgsz={imgsz})")


if __name__ == "__main__":
    main()
