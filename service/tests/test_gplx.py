"""GPLX PET: fixture OCR (nhãn song ngữ, ngày cấp dạng câu) → tự phân loại → bóc tách.
Mô phỏng theo mẫu thật #1 ở docs/samples/gplx-pet-mau-01.md (LÂM TRỌNG GIANG).
"""
import uuid

from app.extract import LabelAnchoredExtractor
from app.ocr import (
    StubDetector,
    StubQualityChecker,
    StubRectifier,
    StubStructuredReader,
)
from app.ocr.types import OcrLine
from app.pipeline import PipelineEngine
from app.pipeline.classifier import RuleClassifier
from app.plugins import PluginManager
from app.settings import settings


def _l(text, y, x=40, w=420, h=28, conf=0.95):
    return OcrLine(text=text, x=x, y=y, w=w, h=h, confidence=conf)


GPLX_LINES = [
    _l("BỘ GTVT", 20, w=120),
    _l("GIẤY PHÉP LÁI XE/DRIVER'S LICENSE", 45, w=460),
    _l("Số/No: 010114000119", 85),
    _l("Họ tên/Full name: LÂM TRỌNG GIANG", 125),
    _l("Ngày sinh/Date of Birth: 16/01/1988", 165),
    _l("Quốc tịch/Nationality: VIỆT NAM", 205),
    _l("Nơi cư trú/Address: P. Đức Giang, Q. Long Biên, TP. Hà Nội", 245, w=520),
    _l("Hạng/Class: B2", 300, w=160),
    _l("Có giá trị đến/Expires: 19/12/2022", 340),
    _l("Hà Nội, ngày/date 19 tháng/month 12 năm/year 2012", 380, w=520),
]


class FixtureOcr:
    def __init__(self, lines):
        self._lines = lines

    def recognize(self, image, assume_upright=False):
        return list(self._lines)


def _engine(ocr):
    plugins = PluginManager(settings.plugins_dir)
    plugins.load_all()
    return PipelineEngine(
        plugins=plugins,
        quality=StubQualityChecker(),
        detector=StubDetector(),
        rectifier=StubRectifier(),
        classifier=RuleClassifier(plugins),
        structured=StubStructuredReader(),
        ocr=ocr,
        extractor=LabelAnchoredExtractor(),
    )


def test_gplx_auto_classify_and_extract():
    resp = _engine(FixtureOcr(GPLX_LINES)).run(str(uuid.uuid4()), image=None)
    assert resp.documentType == "gplx_pet"
    f = resp.fields
    assert f["idNumber"].value == "010114000119"
    assert f["fullName"].value == "LÂM TRỌNG GIANG"
    assert f["dateOfBirth"].value == "1988-01-16"
    assert f["nationality"].value == "VIỆT NAM"
    assert f["placeOfResidence"].value == "P. Đức Giang, Q. Long Biên, TP. Hà Nội"
    assert f["licenseClass"].value == "B2"
    assert f["dateOfIssue"].value == "2012-12-19"
    assert f["dateOfExpiry"].value == "2022-12-19"
    # Thẻ đã hết hạn 2022 → cảnh báo; thứ tự ngày hợp lệ → không cảnh báo cross-check
    assert "da_het_han" in resp.warnings
    assert not any(w.startswith("thu_tu_ngay_sai") for w in resp.warnings)


def test_gplx_invalid_class_warns():
    bad = [_l("Hạng/Class: XYZ", 300) if "Hạng" in ln.text else ln for ln in GPLX_LINES]
    resp = _engine(FixtureOcr(bad)).run(str(uuid.uuid4()), image=None)
    assert "licenseClass_ngoai_danh_muc" in resp.warnings
