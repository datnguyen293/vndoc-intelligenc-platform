"""Đánh giá END-TO-END: nắn CLASSIC vs CORNER-ONNX trên TOÀN BỘ ảnh golden (local).

Với mỗi mẫu golden có ảnh local: chạy pipeline (OCR + trích xuất anchor) 2 lần và đếm số
trường KHỚP giá trị vàng. So corner có ≥ classic không (không phá loại nào).

Lưu ý leakage: ảnh golden cũng là NGUỒN của synth → corner "đã thấy" thẻ (dạng warp) → kết
quả có phần lạc quan; vẫn là kiểm chức năng hợp lệ.

Chạy: DIP_OCR_BACKEND=vietocr DIP_OCR_DEVICE=cpu python eval_golden.py
"""
from __future__ import annotations

import glob
import os
import sys
import uuid

import cv2
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "service", "tests")))
os.environ.setdefault("DIP_OCR_BACKEND", "vietocr")
os.environ.setdefault("DIP_OCR_DEVICE", "cpu")

from app.cv import build_preprocessors  # noqa: E402
from app.extract import LabelAnchoredExtractor  # noqa: E402
from app.ocr import StubDetector, StubQualityChecker, StubRectifier, create_ocr_engine  # noqa: E402
from app.pipeline import PipelineEngine  # noqa: E402
from app.pipeline.classifier import RuleClassifier  # noqa: E402
from app.plugins import PluginManager  # noqa: E402
from app.settings import settings  # noqa: E402
from app.structured import RealStructuredReader  # noqa: E402
from test_golden_extract import GOLDEN  # noqa: E402

from corner_onnx import CornerDetectorONNX  # noqa: E402

SAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "service", "samples"))


def _find_image(stem: str) -> str | None:
    folder, _, name = stem.partition("__")
    for ext in ("jpg", "jpeg", "png", "webp"):
        hits = glob.glob(os.path.join(SAMPLES, folder, name + "." + ext))
        if hits:
            return hits[0]
    return None


def _matches(resp, expected: dict) -> int:
    return sum(1 for k, v in expected.items() if resp.fields.get(k) and resp.fields[k].value == v
               or (v is None and (k not in resp.fields or resp.fields[k].value is None)))


def main() -> None:
    det = CornerDetectorONNX("runs/finetune/weights/best.onnx")
    plugins = PluginManager(settings.plugins_dir)
    plugins.load_all()
    ocr = create_ocr_engine()
    detector, classic_rect = build_preprocessors(settings.card_detect)
    shared = dict(plugins=plugins, quality=StubQualityChecker(), classifier=RuleClassifier(plugins),
                  structured=RealStructuredReader(plugins), ocr=ocr, extractor=LabelAnchoredExtractor())
    eng_classic = PipelineEngine(detector=detector, rectifier=classic_rect, **shared)
    eng_stub = PipelineEngine(detector=StubDetector(), rectifier=StubRectifier(), **shared)

    tot_c = tot_k = tot_n = 0
    nocard = 0
    print(f"{'mẫu':34} | classic | corner | tổng")
    for stem, exp in GOLDEN.items():
        img = _find_image(stem)
        if img is None:
            continue
        expected = {k: v for k, v in exp.items() if k not in ("_type", "_hint")}
        hint = exp.get("_hint") or exp.get("_type")
        n = len(expected)

        rc = eng_classic.run(str(uuid.uuid4()), Image.open(img).convert("RGB"), hint)
        cc = _matches(rc, expected)

        warped = det.rectify(cv2.imread(img))
        if warped is None:
            ck = 0
            nocard += 1
        else:
            rk = eng_stub.run(str(uuid.uuid4()), Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)), hint)
            ck = _matches(rk, expected)

        flag = "" if ck >= cc else "  ⬇"
        print(f"{stem:34} | {cc:4}/{n:<2} | {ck:4}/{n:<2} |{flag}")
        tot_c += cc; tot_k += ck; tot_n += n

    print("-" * 60)
    print(f"{'TỔNG':34} | {tot_c:4}/{tot_n:<2} | {tot_k:4}/{tot_n:<2} | corner NO-CARD: {nocard}")


if __name__ == "__main__":
    main()
