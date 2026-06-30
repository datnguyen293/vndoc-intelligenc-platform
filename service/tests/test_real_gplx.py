"""Hồi quy GPLX trên ẢNH THẬT (samples/bang-lai-xe) với OCR thật (RapidOCR).

RapidOCR (đa ngữ) đọc kém một số trường GPLX (số GPLX, ngày cấp dạng câu) — chỉ assert
các trường RapidOCR ổn định: loại + ngày sinh + hạng + hết hạn. (Trường đầy đủ + có dấu
cần VietOCR — đã kiểm thủ công; logic đầy đủ có ở test_gplx.py.)
"""
import os
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

SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "gplx_pet"

EXPECTED = {
    "bang-lai-xe-1.webp": {"dateOfBirth": "1992-12-25", "licenseClass": "B1", "dateOfExpiry": "2052-12-25"},
    "bang-lai-xe-2.webp": {"dateOfBirth": "1988-01-16", "licenseClass": "B2", "dateOfExpiry": "2022-12-19"},
    "bang-lai-xe-3.webp": {"dateOfBirth": "1988-02-15", "licenseClass": "D", "dateOfExpiry": "2022-11-14"},
}


@pytest.fixture(scope="module")
def engine():
    os.environ["DIP_OCR_BACKEND"] = "rapid"
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
def test_real_gplx(engine, name):
    path = SAMPLES / name
    if not path.exists():
        pytest.skip(f"thiếu ảnh mẫu: {path}")
    resp = engine.run(str(uuid.uuid4()), Image.open(path).convert("RGB"))
    assert resp.documentType == "gplx_pet"  # tự nhận loại
    for field, expected in EXPECTED[name].items():
        assert resp.fields[field].value == expected, f"{name}:{field}"
