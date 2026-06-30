"""CCCD/Căn cước QR + OCR bù trên ẢNH THẬT (cần zxing-cpp). OCR dùng fixture đóng băng
nên KHÔNG cần model; ảnh thật chỉ để giải QR. Ảnh .gitignore → clone mới sẽ skip.

Xác minh: QR (cccd_qr) cho định danh có dấu + đúng documentType qua anchor OCR; phân biệt
được chip mặt trước (cũ) vs Căn cước mặt sau (mới) dù QR cùng định dạng.
"""
import json
import uuid
from pathlib import Path

import pytest

pytest.importorskip("zxingcpp")

pytestmark = pytest.mark.slow

from PIL import Image  # noqa: E402

from app.extract import LabelAnchoredExtractor  # noqa: E402
from app.ocr import StubDetector, StubQualityChecker, StubRectifier  # noqa: E402
from app.ocr.types import OcrLine  # noqa: E402
from app.pipeline import PipelineEngine  # noqa: E402
from app.pipeline.classifier import RuleClassifier  # noqa: E402
from app.plugins import PluginManager  # noqa: E402
from app.settings import settings  # noqa: E402
from app.structured import RealStructuredReader  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "ocr"


class _FixtureOcr:
    def __init__(self, lines):
        self._lines = lines

    def recognize(self, image):
        return list(self._lines)


@pytest.fixture(scope="module")
def plugins():
    pm = PluginManager(settings.plugins_dir)
    pm.load_all()
    return pm


def _run(plugins, stem, img_path):
    if not img_path.exists():
        pytest.skip(f"thiếu ảnh mẫu: {img_path}")
    lines = [OcrLine(**l) for l in json.loads((FIX / f"{stem}.json").read_text("utf-8"))["lines"]]
    engine = PipelineEngine(
        plugins=plugins, quality=StubQualityChecker(), detector=StubDetector(),
        rectifier=StubRectifier(), classifier=RuleClassifier(plugins),
        structured=RealStructuredReader(plugins), ocr=_FixtureOcr(lines),
        extractor=LabelAnchoredExtractor(),
    )
    return engine.run(str(uuid.uuid4()), Image.open(img_path).convert("RGB"), doc_type_hint="cccd")


def test_chip_front_qr_plus_ocr(plugins):
    r = _run(plugins, "cccd_chip_front__tien-dat", ROOT / "samples/cccd_chip_front/tien-dat.jpeg")
    assert r.documentType == "cccd_chip_front"
    assert r.structuredDataUsed == ["qr"]
    f = r.fields
    assert f["idNumber"].value == "024088010438" and f["idNumber"].source == "structured"
    assert f["fullName"].value == "Nguyễn Tiến Đạt"          # có dấu (từ QR)
    assert f["oldIdNumber"].value == "121647952"             # số CMND cũ — chỉ QR có
    assert f["dateOfIssue"].value == "2022-06-22"            # chỉ QR có
    assert f["dateOfExpiry"].value == "2028-03-29"           # OCR bù


def test_can_cuoc_back_qr_plus_ocr(plugins):
    r = _run(plugins, "cccd_2024_back__dinh-nam", ROOT / "samples/cccd_2024_back/dinh-nam.jpeg")
    assert r.documentType == "cccd_2024_back"               # phân biệt với chip front
    assert r.structuredDataUsed == ["qr"]
    f = r.fields
    assert f["idNumber"].value == "026099003333" and f["idNumber"].source == "structured"
    assert f["fullName"].value == "Lương Đình Nam"           # có dấu (từ QR, không từ MRZ)
    assert f["placeOfBirth"].value == "Tân Phú, Vĩnh Tường, Vĩnh Phúc"   # OCR bù
    assert f["dateOfExpiry"].value == "2039-12-30"           # OCR bù (QR không có hạn)
