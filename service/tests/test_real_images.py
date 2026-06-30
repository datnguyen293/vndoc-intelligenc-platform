"""Hồi quy trên ẢNH THẬT (samples/the-dang-vien) với OCR thật (RapidOCR/ONNX).

Chỉ assert các trường **ổn định, độc lập dấu**: số thẻ + ngày tháng. Các trường text
có dấu (họ tên, địa chỉ) phụ thuộc chất lượng recognition (VietOCR) nên không assert ở đây.

Bỏ qua nếu chưa cài rapidocr-onnxruntime hoặc thiếu ảnh mẫu.
"""
import uuid
from pathlib import Path

import pytest

pytest.importorskip("rapidocr_onnxruntime")

pytestmark = pytest.mark.slow  # nạp RapidOCR + OCR thật → chỉ chạy khi --runslow

from PIL import Image  # noqa: E402

from app.extract import LabelAnchoredExtractor  # noqa: E402
from app.ocr import (  # noqa: E402
    StubDetector,
    StubQualityChecker,
    StubRectifier,
    StubStructuredReader,
    create_ocr_engine,
)
from app.pipeline import PipelineEngine  # noqa: E402
from app.pipeline.classifier import RuleClassifier  # noqa: E402
from app.plugins import PluginManager  # noqa: E402
from app.settings import settings  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "the_dang_vien"

EXPECTED = {
    "thuy-giang.jpg": {
        "cardNumber": "83.060977",
        "dateOfBirth": "1992-09-24",
        "partyJoinDate": "2023-05-19",
        "officialDate": "2024-05-19",
        "dateOfIssue": "2024-11-07",
    },
    "thedangvien-732782.jpg": {
        "cardNumber": "40.140050",
        "dateOfBirth": "1974-01-22",
        "partyJoinDate": "2007-08-24",
        "officialDate": "2008-08-24",
        "dateOfIssue": "2008-11-07",
    },
}


@pytest.fixture(scope="module")
def engine():
    import os
    os.environ["DIP_OCR_BACKEND"] = "rapid"  # tất định + nhanh (không cần torch)
    plugins = PluginManager(settings.plugins_dir)
    plugins.load_all()
    return PipelineEngine(
        plugins=plugins,
        quality=StubQualityChecker(),
        detector=StubDetector(),
        rectifier=StubRectifier(),
        classifier=RuleClassifier(plugins),
        structured=StubStructuredReader(),
        ocr=create_ocr_engine(),
        extractor=LabelAnchoredExtractor(),
    )


@pytest.mark.parametrize("name", list(EXPECTED))
def test_real_dang_vien(engine, name):
    path = SAMPLES / name
    if not path.exists():
        pytest.skip(f"thiếu ảnh mẫu: {path}")
    resp = engine.run(str(uuid.uuid4()), Image.open(path).convert("RGB"))  # KHÔNG hint
    assert resp.documentType == "the_dang_vien"  # tự nhận loại
    for field, expected in EXPECTED[name].items():
        assert resp.fields[field].value == expected, f"{name}:{field}"
