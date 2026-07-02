"""Train orientation-classifier: MobileNetV3-small (4 lớp: 0/90/180/270), CPU.

Transfer-learning nếu tải được weights pretrained (có mạng); không thì train from scratch.
Augment KHÔNG xoay (xoay chính là nhãn) — chỉ jitter sáng/tương phản/mờ/nhiễu để bền.

Chạy:  PY=../../build/stage/runtime/python.exe ; $PY train.py --data data --epochs 25
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import mobilenet_v3_small

HERE = Path(__file__).resolve().parent
CLASSES = ["0", "180", "270", "90"]  # ImageFolder sắp theo alphabet — nhớ ánh xạ khi export


def build_model(pretrained: bool) -> nn.Module:
    weights = None
    if pretrained:
        try:
            from torchvision.models import MobileNet_V3_Small_Weights
            weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
        except Exception as exc:  # noqa: BLE001
            print("Không tải được pretrained (%s) → train from scratch" % exc)
    m = mobilenet_v3_small(weights=weights)
    m.classifier[3] = nn.Linear(m.classifier[3].in_features, 4)
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data"))
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--imgsz", type=int, default=160)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=6e-4)
    ap.add_argument("--no-pretrained", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(0)
    mean, std = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
    train_tf = transforms.Compose([
        transforms.Resize((args.imgsz, args.imgsz)),
        transforms.ColorJitter(0.3, 0.3, 0.3, 0.05),
        transforms.RandomApply([transforms.GaussianBlur(3, (0.1, 2.0))], p=0.4),
        transforms.RandomAdjustSharpness(0.5, p=0.3),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.12)),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((args.imgsz, args.imgsz)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])

    data = Path(args.data)
    train_ds = ImageFolder(data / "train", transform=train_tf)
    val_ds = ImageFolder(data / "val", transform=eval_tf)
    print("classes (ImageFolder order):", train_ds.classes)
    print(f"train={len(train_ds)}  val={len(val_ds)}")

    train_dl = DataLoader(train_ds, batch_size=args.bs, shuffle=True, num_workers=0)
    val_dl = DataLoader(val_ds, batch_size=args.bs, num_workers=0)

    model = build_model(not args.no_pretrained)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    lossf = nn.CrossEntropyLoss()

    best = 0.0
    (HERE / "runs").mkdir(exist_ok=True)
    for ep in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for x, y in train_dl:
            opt.zero_grad()
            loss = lossf(model(x), y)
            loss.backward()
            opt.step()
            tot += loss.item() * x.size(0)
        sched.step()

        model.eval()
        correct = n = 0
        with torch.no_grad():
            for x, y in val_dl:
                pred = model(x).argmax(1)
                correct += (pred == y).sum().item()
                n += y.size(0)
        acc = correct / max(n, 1)
        print(f"ep {ep:2}/{args.epochs}  loss={tot/len(train_ds):.4f}  val_acc={acc:.3f}")
        if acc >= best:
            best = acc
            torch.save({"state_dict": model.state_dict(),
                        "classes": train_ds.classes, "imgsz": args.imgsz},
                       HERE / "runs" / "best.pt")
    print(f"BEST val_acc={best:.3f} → runs/best.pt")


if __name__ == "__main__":
    main()
