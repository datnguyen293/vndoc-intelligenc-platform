"""So sánh nắn ảnh CLASSIC vs CORNER-MODEL trên ảnh thật, đo bằng ANCHOR (số trường bóc ra).

Với mỗi ảnh: chạy pipeline (OCR + classify + trích xuất anchor) 2 lần —
  (A) rectifier classic hiện tại,
  (B) nắn theo 4 góc model rồi feed ảnh đã nắn (StubRectifier).
In số trường non-null + documentType, và lưu montage [góc | nắn-corner | nắn-classic].

Chạy:  DIP_OCR_BACKEND=vietocr python evaluate.py --weights runs/pose/weights/best.pt \
          --images ../../service/samples/the_quan_nhan/cuong.jpeg[:hint] ...
Không truyền --images → quét vài mẫu có NỀN NHIỄU (test thật, ngoài phân phối tổng hợp).
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "service")))
os.environ.setdefault("DIP_OCR_BACKEND", "vietocr")

from PIL import Image  # noqa: E402

from app.cv import build_preprocessors  # noqa: E402
from app.extract import LabelAnchoredExtractor  # noqa: E402
from app.ocr import StubDetector, StubQualityChecker, StubRectifier, create_ocr_engine  # noqa: E402
from app.pipeline import PipelineEngine  # noqa: E402
from app.pipeline.classifier import RuleClassifier  # noqa: E402
from app.plugins import PluginManager  # noqa: E402
from app.settings import settings  # noqa: E402
from app.structured import RealStructuredReader  # noqa: E402

from corner_rectify import CornerRectifier  # noqa: E402

# Mẫu có NỀN NHIỄU / cầm tay (test thật): folder → hint.
DEFAULT = [
    ("../../service/samples/the_quan_nhan/cuong.jpeg", "the_quan_nhan"),
    ("../../service/samples/gplx_pet/tien-dat.jpeg", "gplx_pet"),
]


def _pil(bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def _nfields(resp) -> tuple[str, int, dict]:
    got = {k: v.value for k, v in resp.fields.items() if v.value}
    return resp.documentType, len(got), got


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="runs/pose/weights/best.pt")
    ap.add_argument("--images", nargs="*", help="path[:hint] ...")
    ap.add_argument("--out", default="eval_out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    items = []
    for it in (args.images or []):
        path, _, hint = it.partition(":")
        items.append((path, hint or None))
    if not items:
        items = DEFAULT

    plugins = PluginManager(settings.plugins_dir)
    plugins.load_all()
    ocr = create_ocr_engine()
    detector, classic_rect = build_preprocessors(settings.card_detect)
    shared = dict(plugins=plugins, quality=StubQualityChecker(), classifier=RuleClassifier(plugins),
                  structured=RealStructuredReader(plugins), ocr=ocr, extractor=LabelAnchoredExtractor())
    eng_classic = PipelineEngine(detector=detector, rectifier=classic_rect, **shared)
    eng_stub = PipelineEngine(detector=StubDetector(), rectifier=StubRectifier(), **shared)

    rect = CornerRectifier(args.weights)

    print(f"{'ảnh':40} | {'CLASSIC':26} | {'CORNER-MODEL':26}")
    for path, hint in items:
        if not os.path.exists(path):
            print(f"{os.path.basename(path):40} | (thiếu ảnh)"); continue
        bgr = cv2.imread(path)
        name = os.path.basename(path)

        # (A) classic
        ta, na, _ = _nfields(eng_classic.run(str(uuid.uuid4()), Image.open(path).convert("RGB"), hint))
        # (B) corner-model
        warped = rect.rectify(bgr)
        if warped is None:
            tb, nb = "no-card", 0
        else:
            cv2.imwrite(os.path.join(args.out, f"{name}.corner.jpg"), warped)
            tb, nb, _ = _nfields(eng_stub.run(str(uuid.uuid4()), _pil(warped), hint))
        cv2.imwrite(os.path.join(args.out, f"{name}.corners.jpg"), rect.draw(bgr))

        print(f"{name:40} | {ta:16} {na:>2} trường | {tb:16} {nb:>2} trường")

    print(f"\nMontage/ảnh nắn lưu ở: {args.out}/  (xem *.corners.jpg = góc detect, *.corner.jpg = ảnh nắn)")


if __name__ == "__main__":
    main()
