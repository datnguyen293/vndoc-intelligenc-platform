"""Thẻ Đảng viên MẪU MỚI: QR-first trên ẢNH THẬT (cần zxing-cpp) → slow test.

Mẫu mới có QR bề mặt ĐỦ 7 trường (đầy đủ hơn OCR: có officialDate + partyOrganization
không cụt). Chiến lược: đọc được QR → lấy TOÀN BỘ từ QR, BỎ QUA OCR (structuredComplete).
QR nhỏ trong ảnh 1600px → identify upscale khi hint=the_dang_vien. Ảnh mẫu bị .gitignore.
"""
import uuid
from pathlib import Path

import pytest

pytest.importorskip("zxingcpp")

pytestmark = pytest.mark.slow

from PIL import Image  # noqa: E402

from app.extract import LabelAnchoredExtractor  # noqa: E402
from app.ocr import StubDetector, StubQualityChecker, StubRectifier  # noqa: E402
from app.pipeline import PipelineEngine  # noqa: E402
from app.pipeline.classifier import RuleClassifier  # noqa: E402
from app.plugins import PluginManager  # noqa: E402
from app.settings import settings  # noqa: E402
from app.structured import RealStructuredReader  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "the_dang_vien"


@pytest.fixture(scope="module")
def plugins():
    pm = PluginManager(settings.plugins_dir)
    pm.load_all()
    return pm


class _SpyOcr:
    def __init__(self) -> None:
        self.called = False

    def recognize(self, image, assume_upright=False):
        self.called = True
        return []


def _img(name):
    path = SAMPLES / name
    if not path.exists():
        pytest.skip(f"thiếu ảnh mẫu: {path}")
    return Image.open(path).convert("RGB")


@pytest.mark.parametrize("name", ["ngoc-hung.jpeg", "ngoc-hung-270.jpeg"])
def test_qr_first_skips_ocr(plugins, name):
    spy = _SpyOcr()
    engine = PipelineEngine(
        plugins=plugins, quality=StubQualityChecker(), detector=StubDetector(),
        rectifier=StubRectifier(), classifier=RuleClassifier(plugins),
        structured=RealStructuredReader(plugins), ocr=spy,
        extractor=LabelAnchoredExtractor(),
    )
    # hint=the_dang_vien (client gửi loại cụ thể) → identify upscale bắt QR → bỏ OCR.
    resp = engine.run(str(uuid.uuid4()), _img(name), doc_type_hint="the_dang_vien")

    assert spy.called is False                       # QR đọc được → KHÔNG OCR
    assert resp.documentType == "the_dang_vien"
    assert resp.structuredDataUsed == ["qr"]
    f = resp.fields
    assert f["cardNumber"].value == "001088023765" and f["cardNumber"].source == "structured"
    assert f["fullName"].value == "NGUYỄN NGỌC HƯNG"
    assert f["dateOfBirth"].value == "1988-02-13"        # QR ddMMyyyy → ISO
    assert f["partyJoinDate"].value == "2011-06-14"
    assert f["officialDate"].value == "2012-06-14"       # QR có, OCR bề mặt KHÔNG có
    assert f["partyOrganization"].value == "Đảng Bộ Công An Trung Ương"  # ĐẦY ĐỦ (OCR bị cụt)
    assert f["dateOfIssue"].value == "2025-09-14"
    # QR không có quê quán → null trên đường QR (theo thiết kế).
    assert f["placeOfOrigin"].value is None
