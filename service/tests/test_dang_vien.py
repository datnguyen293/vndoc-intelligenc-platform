"""End-to-end Thẻ Đảng viên: OCR (fixture mô phỏng PaddleOCR theo thẻ thật) →
phân loại thuần luật (RuleClassifier, KHÔNG hint) → label-anchored → JSON.
Chứng minh đường tự-nhận-loại + bóc tách thật mà không cần model.
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


def _line(text, x, y, w=180, h=28, conf=0.96):
    return OcrLine(text=text, x=x, y=y, w=w, h=h, confidence=conf)


# Mô phỏng đầu ra OCR cho thẻ Đảng viên thật (NGUYỄN THÙY GIANG)
DANG_VIEN_LINES = [
    _line("THẺ ĐẢNG VIÊN", 300, 40, 260, 40, 0.97),
    _line("Số", 80, 110, 40),
    _line("83.060977", 170, 110, 160),
    _line("Họ và tên", 80, 165, 130),
    _line("NGUYỄN THÙY GIANG", 260, 165, 300),
    _line("Sinh ngày", 80, 220, 120),
    _line("24 - 09 - 1992", 260, 220, 180),
    _line("Quê quán", 80, 275, 120),
    _line("X. Tân Triều,", 260, 275, 170),
    _line("H. Thanh Trì, TP. Hà Nội", 260, 308, 300),
    _line("Vào Đảng ngày", 80, 360, 160),
    _line("19 - 05 - 2023", 300, 360, 180),
    _line("Chính thức ngày", 80, 405, 170),
    _line("19 - 05 - 2024", 300, 405, 180),
    _line("Nơi cấp thẻ", 80, 455, 150),
    _line("Đảng bộ Khối", 300, 455, 180),
    _line("các cơ quan Trung ương", 300, 488, 280),
    _line("Ngày 07 tháng 11 năm 2024", 260, 545, 330, 30),
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
        classifier=RuleClassifier(plugins),  # tự phân loại, không hint
        structured=StubStructuredReader(),
        ocr=ocr,
        extractor=LabelAnchoredExtractor(),
    )


def test_auto_classify_and_extract():
    engine = _engine(FixtureOcr(DANG_VIEN_LINES))
    resp = engine.run(str(uuid.uuid4()), image=None)  # KHÔNG truyền hint

    assert resp.documentType == "the_dang_vien"  # tự nhận loại từ "THẺ ĐẢNG VIÊN"
    f = resp.fields
    assert f["cardNumber"].value == "83.060977"
    assert f["fullName"].value == "NGUYỄN THÙY GIANG"
    assert f["dateOfBirth"].value == "1992-09-24"
    assert f["placeOfOrigin"].value == "X. Tân Triều, H. Thanh Trì, TP. Hà Nội"
    assert f["partyJoinDate"].value == "2023-05-19"
    assert f["officialDate"].value == "2024-05-19"
    assert f["partyOrganization"].value == "Đảng bộ Khối các cơ quan Trung ương"
    assert f["dateOfIssue"].value == "2024-11-07"
    assert resp.errors == []
    assert not any(w.startswith("thu_tu_ngay_sai") for w in resp.warnings)


def test_missing_required_warns():
    lines = [ln for ln in DANG_VIEN_LINES if ln.text != "NGUYỄN THÙY GIANG"]
    engine = _engine(FixtureOcr(lines))
    resp = engine.run(str(uuid.uuid4()), image=None)
    assert resp.fields["fullName"].value is None
    assert "fullName_thieu" in resp.warnings
    assert resp.fields["cardNumber"].value == "83.060977"


def test_crosscheck_bad_date_order():
    # Chính thức (2022) TRƯỚC vào Đảng (2023) → vô lý → cảnh báo
    lines = [
        _line("19 - 05 - 2022", 300, 405, 180) if ln.text == "19 - 05 - 2024" else ln
        for ln in DANG_VIEN_LINES
    ]
    engine = _engine(FixtureOcr(lines))
    resp = engine.run(str(uuid.uuid4()), image=None)
    assert any("thu_tu_ngay_sai" in w for w in resp.warnings)
