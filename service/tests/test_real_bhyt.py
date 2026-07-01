"""BHYT QR-first trên ẢNH THẬT (cần zxing-cpp) → slow test, KHÔNG cần model OCR.

Xác minh chiến lược chốt với anh Đạt: đọc được QR → lấy TOÀN BỘ từ QR và BỎ QUA OCR.
Ảnh mẫu bị .gitignore nên clone mới/CI sẽ skip.
"""
import uuid
from pathlib import Path

import pytest

pytest.importorskip("zxingcpp")  # đọc QR thật → bỏ qua nếu chưa cài

pytestmark = pytest.mark.slow

from PIL import Image  # noqa: E402

from app.extract import LabelAnchoredExtractor  # noqa: E402
from app.ocr import StubDetector, StubQualityChecker, StubRectifier  # noqa: E402
from app.pipeline import PipelineEngine  # noqa: E402
from app.pipeline.classifier import RuleClassifier  # noqa: E402
from app.plugins import PluginManager  # noqa: E402
from app.settings import settings  # noqa: E402
from app.structured import RealStructuredReader  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "bhyt"


@pytest.fixture(scope="module")
def plugins():
    pm = PluginManager(settings.plugins_dir)
    pm.load_all()
    return pm


@pytest.fixture(scope="module")
def reader(plugins):
    return RealStructuredReader(plugins)


class _SpyOcr:
    """OCR gián điệp: nếu bị gọi nghĩa là fast-path QR KHÔNG hoạt động → fail."""

    def __init__(self) -> None:
        self.called = False

    def recognize(self, image):
        self.called = True
        return []


def _img(name):
    path = SAMPLES / name
    if not path.exists():
        pytest.skip(f"thiếu ảnh mẫu: {path}")
    return Image.open(path).convert("RGB")


@pytest.mark.parametrize("name", ["tien-dat.jpeg", "tien-dat-90.jpeg"])
def test_identify_from_qr(reader, name):
    doc_type, fields, used = reader.identify(_img(name))
    assert doc_type == "bhyt"
    assert used == ["qr"]
    assert fields["idNumber"] == "0111077012"
    assert fields["fullName"] == "Nguyễn Tiến Đạt"


@pytest.mark.parametrize("name", ["tien-dat.jpeg", "tien-dat-90.jpeg"])
def test_pipeline_qr_first_skips_ocr(plugins, name):
    spy = _SpyOcr()
    engine = PipelineEngine(
        plugins=plugins,
        quality=StubQualityChecker(),
        detector=StubDetector(),
        rectifier=StubRectifier(),
        classifier=RuleClassifier(plugins),
        structured=RealStructuredReader(plugins),
        ocr=spy,
        extractor=LabelAnchoredExtractor(),
    )
    resp = engine.run(str(uuid.uuid4()), _img(name))

    assert spy.called is False                      # OCR bị BỎ QUA khi QR đọc được
    assert resp.documentType == "bhyt"
    assert resp.structuredDataUsed == ["qr"]
    f = resp.fields
    assert f["idNumber"].value == "0111077012" and f["idNumber"].source == "structured"
    assert f["fullName"].value == "Nguyễn Tiến Đạt"
    assert f["dateOfBirth"].value == "1988-03-29"   # QR dd/MM/yyyy → ISO
    assert f["sex"].value == "Nam"
    assert f["dateOfIssue"].value == "2023-07-31"
    assert f["issuePlace"].value == "Quận Cầu Giấy, Thành phố Hà Nội"
    # QR KHÔNG chứa 2 trường này → null trên đường QR (theo thiết kế).
    assert f["registeredHospital"].value is None
    assert f["benefitLevel"].value is None


# Thẻ BHYT MẪU CŨ: mã số 15 ký tự (2 chữ + 13 số), vẫn QR-first.
_OLD = [
    ("bhyt-1.jpeg", "HS4010120878837", "Vũ Xuân Minh"),
    ("bhyt-2.jpeg", "HC4252516019894", "Đỗ Thu Hằng"),
    ("tran-thi-b.jpeg", "DN4797911013123", "Trần Thị Thanh Thùy"),
]


@pytest.mark.parametrize("name,idnum,fullname", _OLD)
def test_old_model_qr_first(plugins, name, idnum, fullname):
    spy = _SpyOcr()
    engine = PipelineEngine(
        plugins=plugins, quality=StubQualityChecker(), detector=StubDetector(),
        rectifier=StubRectifier(), classifier=RuleClassifier(plugins),
        structured=RealStructuredReader(plugins), ocr=spy,
        extractor=LabelAnchoredExtractor(),
    )
    resp = engine.run(str(uuid.uuid4()), _img(name))
    assert spy.called is False
    assert resp.documentType == "bhyt"
    assert resp.structuredDataUsed == ["qr"]
    f = resp.fields
    assert f["idNumber"].value == idnum and f["idNumber"].source == "structured"  # 15 ký tự
    assert f["fullName"].value == fullname
    assert f["placeOfResidence"].value                    # mẫu cũ: QR [4] có địa chỉ


def test_qr_fallback_to_original(reader):
    # Ảnh chính (bản rectify) None/mất QR → dùng ảnh GỐC (image_alt) để giải QR.
    img = _img("bhyt-1.jpeg")
    ident = reader.identify(None, image_alt=img)
    assert ident is not None
    doc_type, fields, _used = ident
    assert doc_type == "bhyt" and fields["idNumber"] == "HS4010120878837"


def test_unknown_doctype_returns_empty(reader):
    assert reader.read(None, "khong_ton_tai") == ({}, [])
    assert reader.identify(None) is None
