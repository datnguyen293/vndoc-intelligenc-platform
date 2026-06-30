"""Phân loại CCCD/CMND tự động từ hint thô (cmnd/cccd) — THUẦN luật, KHÔNG cần model.

Mô phỏng dấu hiệu OCR đặc trưng từng loại (đã quan sát trên ảnh mẫu thật).
"""
import pytest

from app.ocr.types import OcrLine
from app.pipeline.classifier import RuleClassifier
from app.plugins import PluginManager
from app.settings import settings


@pytest.fixture(scope="module")
def clf():
    pm = PluginManager(settings.plugins_dir)
    pm.load_all()
    return RuleClassifier(pm)


def _lines(*texts):
    return [OcrLine(t, 0, i * 40, 400, 30, 0.9) for i, t in enumerate(texts)]


def test_cmnd_12_by_length(clf):
    dt, _ = clf.classify(_lines("CHỨNG MINH NHÂN DÂN", "Số: 001192004768"), hint="cmnd")
    assert dt == "cmnd_12"


def test_cmnd_9_fallback_when_no_12_run(clf):
    # Số 9 bị OCR sai → KHÔNG có dãy 12 → rơi về cmnd_9 (fallback).
    dt, _ = clf.classify(_lines("GIẤY CHỨNG MINH NHÂN DÂN", "Số SOMERO1644953"), hint="cmnd")
    assert dt == "cmnd_9"


def test_cccd_chip_front_by_title(clf):
    dt, _ = clf.classify(_lines("CĂN CƯỚC CÔNG DÂN", "Citizen Identity Card"), hint="cccd")
    assert dt == "cccd_chip_front"


def test_cccd_2024_front_excludes_cong_dan(clf):
    # "CĂN CƯỚC" KHÔNG kèm "CÔNG DÂN" + "Số định danh" → Căn cước mới mặt trước.
    dt, _ = clf.classify(_lines("CĂN CƯỚC", "IDENTITY CARD", "Số định danh cá nhân"), hint="cccd")
    assert dt == "cccd_2024_front"


def test_cccd_2024_back_by_mrz_anchors(clf):
    dt, _ = clf.classify(
        _lines("Nơi cư trú", "Nơi đăng ký khai sinh", "BỘ CÔNG AN"), hint="cccd"
    )
    assert dt == "cccd_2024_back"


def test_cong_dan_not_misread_as_2024_front(clf):
    # Ảnh chip cũ (có 'CÔNG DÂN') KHÔNG được nhận thành Căn cước mới (exclude chặn).
    dt, _ = clf.classify(_lines("CĂN CƯỚC CÔNG DÂN", "Số định danh cá nhân"), hint="cccd")
    assert dt == "cccd_chip_front"


def test_unknown_family_member(clf):
    # Hint cccd nhưng không dấu hiệu nào khớp → unknown.
    dt, conf = clf.classify(_lines("XYZ ABC"), hint="cccd")
    assert dt == "unknown" and conf == 0.0
