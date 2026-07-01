"""Train YOLOv8-pose detect 4 góc thẻ (nhánh thử nghiệm).

Khởi từ yolov8n-pose (COCO pretrained backbone) → fine-tune trên dữ liệu tổng hợp 4 keypoint.
Chạy:  python train.py --data data/data.yaml --epochs 60
"""
from __future__ import annotations

import argparse
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/data.yaml")
    ap.add_argument("--model", default="yolov8n-pose.pt", help="COCO pretrained (backbone)")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="0", help="0=GPU, cpu")
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=os.path.join(_HERE, "runs"),   # path tuyệt đối → không lồng runs/runs
        name="pose",
        exist_ok=True,
        # Augment nhẹ tay: dữ liệu tổng hợp đã đa dạng nền/phối cảnh; TẮT lật/mosaic/xoay
        # lớn để không phá định danh keypoint góc.
        fliplr=0.0,
        flipud=0.0,
        mosaic=0.0,
        degrees=0.0,
        perspective=0.0,
        hsv_h=0.015, hsv_s=0.5, hsv_v=0.4,
    )
    print("Train xong → runs/pose/weights/best.pt")


if __name__ == "__main__":
    main()
