"""CLI: chạy pipeline trên một ảnh thật (để test trên máy đã cài PaddleOCR).

Dùng:
    python -m tools.ocr_image /duong/dan/the-dang-vien.jpg --hint the_dang_vien
"""
from __future__ import annotations

import argparse
import json
import uuid

from PIL import Image

from app.cv import build_preprocessors
from app.extract import LabelAnchoredExtractor
from app.ocr import (
    StubQualityChecker,
    create_ocr_engine,
)
from app.pipeline import PipelineEngine
from app.pipeline.classifier import RuleClassifier
from app.plugins import PluginManager
from app.settings import settings
from app.structured import RealStructuredReader


def main() -> None:
    ap = argparse.ArgumentParser(description="Bóc tách 1 ảnh giấy tờ → JSON")
    ap.add_argument("image", help="đường dẫn ảnh (jpg/png)")
    ap.add_argument("--hint", default=None, help="docTypeHint, vd the_dang_vien")
    args = ap.parse_args()

    plugins = PluginManager(settings.plugins_dir)
    plugins.load_all()
    detector, rectifier = build_preprocessors(settings.card_detect)
    engine = PipelineEngine(
        plugins=plugins,
        quality=StubQualityChecker(),
        detector=detector,
        rectifier=rectifier,
        classifier=RuleClassifier(plugins),
        structured=RealStructuredReader(plugins),
        ocr=create_ocr_engine(),
        extractor=LabelAnchoredExtractor(),
    )

    image = Image.open(args.image).convert("RGB")
    resp = engine.run(str(uuid.uuid4()), image, doc_type_hint=args.hint)
    print(json.dumps(resp.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
