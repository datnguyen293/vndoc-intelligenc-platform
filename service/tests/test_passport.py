"""Hộ chiếu VN — OCR vùng nhìn (giả lập) + MRZ TD3, cả 2 layout cũ/mới. KHÔNG cần model.

MRZ đọc từ dòng OCR qua RealStructuredReader; tên từ OCR (MRZ không dấu). Mô phỏng bố cục
nhãn-trên/bên-giá-trị theo docs/samples/ho-chieu-mau-0{1,2}.md.
"""
import uuid

from app.extract import LabelAnchoredExtractor
from app.ocr import StubDetector, StubQualityChecker, StubRectifier
from app.ocr.types import OcrLine
from app.pipeline import PipelineEngine
from app.pipeline.classifier import RuleClassifier
from app.plugins import PluginManager
from app.settings import settings
from app.structured import RealStructuredReader


def _l(text, y, x=100, w=520, h=30, conf=0.95):
    return OcrLine(text, x, y, w, h, conf)


class _FixtureOcr:
    def __init__(self, lines):
        self._lines = lines

    def recognize(self, image):
        return list(self._lines)


def _engine(lines):
    pm = PluginManager(settings.plugins_dir)
    pm.load_all()
    return PipelineEngine(
        plugins=pm, quality=StubQualityChecker(), detector=StubDetector(),
        rectifier=StubRectifier(), classifier=RuleClassifier(pm),
        structured=RealStructuredReader(pm), ocr=_FixtureOcr(lines),
        extractor=LabelAnchoredExtractor(),
    )


# Hộ chiếu MỚI (e-passport): họ/tên tách 2 trường → fullName GHÉP; số ĐDCN 12 số.
NEW = [
    _l("HỘ CHIẾU / PASSPORT", 20),
    _l("Số hộ chiếu / Passport No: E01828939", 60),
    _l("Họ / Surname: NGUYỄN", 100, w=340),
    _l("Chữ đệm và tên / Given names: TIẾN ĐẠT", 140),
    _l("Quốc tịch / Nationality: VIỆT NAM", 180),
    _l("Ngày sinh / Date of birth: 29/03/1988", 220),
    _l("Giới tính / Sex: NAM", 260, w=340),
    _l("Nơi sinh / Place of birth: Bắc Giang", 300),
    _l("Số ĐDCN, CMND / ID No: 024088010438", 340),
    _l("Ngày cấp / Date of issue: 20/05/2024", 380),
    _l("Ngày hết hạn / Date of expiry: 20/05/2034", 420),
    _l("P<VNMNGUYEN<<TIEN<DAT<<<<<<<<<<<<<<<<<<<<<<<<<", 480, w=760),
    _l("E018289390VNM8803296M3405204024088010438<<08", 520, w=760),
]

# Hộ chiếu CŨ: "Họ và tên" 1 trường (nhãn-trên-giá-trị); số GCMND 9 số.
OLD = [
    _l("HỘ CHIẾU / PASSPORT", 20),
    _l("Số hộ chiếu / Passport No: B7849474", 60),
    _l("Họ và tên / Full name", 100, w=300),
    _l("NGUYỄN TIẾN ĐẠT", 135, w=400),
    _l("Ngày sinh / Date of birth: 29/03/1988", 175),
    _l("Giới tính / Sex: NAM", 215, w=340),
    _l("Số GCMND / ID card No: 121647952", 255),
    _l("Ngày cấp / Date of issue: 13/05/2013", 295),
    _l("Có giá trị đến / Date of expiry: 13/05/2023", 335),
    _l("Nơi cấp / Place of issue: Cục Quản lý xuất nhập cảnh", 375),
    _l("P<VNMNGUYEN<<TIEN<DAT<<<<<<<<<<<<<<<<<<<<<<<<<", 430, w=760),
    _l("B7849474<6VNM8803296M2305134121647952<<<<<50", 470, w=760),
]


def test_passport_new_compose_and_mrz():
    r = _engine(NEW).run(str(uuid.uuid4()), image=None)
    assert r.documentType == "passport_vn"
    assert r.structuredDataUsed == ["mrz"]
    f = r.fields
    assert f["idNumber"].value == "E01828939" and f["idNumber"].source == "structured"
    assert f["surname"].value == "NGUYỄN" and f["givenNames"].value == "TIẾN ĐẠT"
    assert f["fullName"].value == "NGUYỄN TIẾN ĐẠT"          # ghép surname + givenNames
    assert f["dateOfBirth"].value == "1988-03-29" and f["dateOfBirth"].source == "structured"
    assert f["dateOfExpiry"].value == "2034-05-20"           # MRZ (structured)
    assert f["personalIdNumber"].value == "024088010438"     # số ĐDCN 12 số (MRZ)
    assert f["dateOfIssue"].value == "2024-05-20"            # OCR (MRZ không có)


def test_passport_old_fullname_and_9digit():
    r = _engine(OLD).run(str(uuid.uuid4()), image=None)
    assert r.documentType == "passport_vn"
    f = r.fields
    assert f["idNumber"].value == "B7849474"
    assert f["fullName"].value == "NGUYỄN TIẾN ĐẠT"          # nhãn "Họ và tên" → dòng dưới
    assert f["personalIdNumber"].value == "121647952"        # số GCMND 9 số
    assert f["dateOfExpiry"].value == "2023-05-13"
    assert "da_het_han" in r.warnings                         # hết hạn 2023
