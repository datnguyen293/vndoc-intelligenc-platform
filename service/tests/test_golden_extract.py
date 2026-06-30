"""Test GOLDEN chống hồi quy shared code (dates.py, anchored.py, normalize.py, classifier).

Chạy bộ phân loại + trích xuất trên **text OCR thật đã đóng băng** (fixtures/ocr/*.json,
chụp từ VietOCR) và so với kết quả vàng. KHÔNG cần model → nhanh, tất định.

➡️ Mọi sửa thư viện dùng chung cho loại giấy tờ MỚI mà làm sai loại CŨ sẽ FAIL ở đây.
Khi cố ý đổi hành vi: chạy lại `tools/capture_ocr.py` + cập nhật GOLDEN có chủ đích.
"""
import json
import uuid
from pathlib import Path

import pytest

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

FIX = Path(__file__).resolve().parent / "fixtures" / "ocr"

# Kết quả vàng = output đã kiểm đúng trên text OCR VietOCR thật (có dấu).
# (Một số nhiễu OCR cố hữu được khóa nguyên trạng: "Hi Hi", "X Hoàng Diệu".)
GOLDEN = {
    "the_dang_vien__thuy-giang": {
        "_type": "the_dang_vien",
        "cardNumber": "83.060977", "fullName": "NGUYỄN THÙY GIANG",
        "dateOfBirth": "1992-09-24",
        "placeOfOrigin": "X. Tân Triều, H. Thanh Trì, TP. Hà Nội",
        "partyJoinDate": "2023-05-19", "officialDate": "2024-05-19",
        "partyOrganization": "Đảng bộ Khối các cơ quan Trung ương",
        "dateOfIssue": "2024-11-07",
    },
    "the_dang_vien__thuy-giang-90": {  # bản XOAY 90° — khóa cả nắn hướng + trích xuất
        "_type": "the_dang_vien",
        "cardNumber": "83.060977", "fullName": "NGUYỄN THÙY GIANG",
        "dateOfBirth": "1992-09-24",
        "placeOfOrigin": "X. Tân Triều, H. Thanh Trì, TP. Hà Nội",
        "partyJoinDate": "2023-05-19", "officialDate": "2024-05-19",
        "partyOrganization": "Đảng bộ Khối các cơ quan Trung ương",
        "dateOfIssue": "2024-11-07",
    },
    "the_dang_vien__thuy-giang-180": {  # XOAY 180°
        "_type": "the_dang_vien",
        "cardNumber": "83.060977", "fullName": "NGUYỄN THÙY GIANG",
        "dateOfBirth": "1992-09-24",
        "placeOfOrigin": "X. Tân Triều, H. Thanh Trì, TP. Hà Nội",
        "partyJoinDate": "2023-05-19", "officialDate": "2024-05-19",
        "partyOrganization": "Đảng bộ Khối các cơ quan Trung ương",
        "dateOfIssue": "2024-11-07",
    },
    "the_dang_vien__thuy-giang-270": {  # XOAY 270°
        "_type": "the_dang_vien",
        "cardNumber": "83.060977", "fullName": "NGUYỄN THÙY GIANG",
        "dateOfBirth": "1992-09-24",
        "placeOfOrigin": "X. Tân Triều, H. Thanh Trì, TP. Hà Nội",
        "partyJoinDate": "2023-05-19", "officialDate": "2024-05-19",
        "partyOrganization": "Đảng bộ Khối các cơ quan Trung ương",
        "dateOfIssue": "2024-11-07",
    },
    "the_dang_vien__thedangvien-732782": {
        "_type": "the_dang_vien",
        "cardNumber": "40.140050", "fullName": "BÙI TRỌNG THANH",
        "dateOfBirth": "1974-01-22",
        "placeOfOrigin": "X. Mậu Lâm Hi Hi Như Thanh, T. Thanh Hóa",
        "partyJoinDate": "2007-08-24", "officialDate": "2008-08-24",
        "partyOrganization": "Đảng bộ T.P Hồ Chí Minh",
        "dateOfIssue": "2008-11-07",
    },
    "gplx_pet__bang-lai-xe-1": {
        "_type": "gplx_pet",
        "idNumber": "990170000806", "fullName": None, "dateOfBirth": "1992-12-25",
        "nationality": "VIỆT NAM",
        "placeOfResidence": "P. Đông Sơn, TP. Thanh Hóa, T. Thanh Hóa",
        "licenseClass": "B1", "dateOfIssue": "2017-02-20", "dateOfExpiry": "2052-12-25",
    },
    "gplx_pet__bang-lai-xe-2": {
        "_type": "gplx_pet",
        "idNumber": "010111000119", "fullName": "LÂM TRỌNG GIANG",
        "dateOfBirth": "1988-01-16", "nationality": "VIỆT NAM",
        "placeOfResidence": "P. Đức Giang, Q. Long Biên, TP. Hà Nội",
        "licenseClass": "B2", "dateOfIssue": "2012-12-19", "dateOfExpiry": "2022-12-19",
    },
    "gplx_pet__bang-lai-xe-3": {
        "_type": "gplx_pet",
        "idNumber": "010103033708", "fullName": "NGUYỄN ĐÌNH TÙNG",
        "dateOfBirth": "1988-02-15", "nationality": "VIỆT NAM",
        "placeOfResidence": "X Hoàng Diệu, H. Chương Mỹ, TP. Hà Nội",
        "licenseClass": "D", "dateOfIssue": "2017-11-14", "dateOfExpiry": "2022-11-14",
    },
    "gplx_pet__tien-dat": {  # GPLX khó: box nhiễu giữa nhãn-giá trị, địa chỉ wrap 2 dòng
        "_type": "gplx_pet",
        "idNumber": "010231030002", "fullName": "NGUYỄN TIẾN ĐẠT",
        "dateOfBirth": "1988-03-29", "nationality": "VIỆT NAM",
        "placeOfResidence": "Tân Lập X. Lam Cốt, H. Tân Yên, T. Bắc Giang",
        "licenseClass": "B2", "dateOfIssue": "2023-04-21", "dateOfExpiry": "2033-04-21",
    },
    "gplx_pet__thuy-giang": {  # GPLX: địa chỉ wrap, dòng dưới thụt lệch cột nhãn
        "_type": "gplx_pet",
        "idNumber": "011230007240", "fullName": "NGUYỄN THỦY GIANG",
        "dateOfBirth": "1992-09-24", "nationality": "VIỆT NAM",
        "placeOfResidence": "P29 B12, TT Kim Liên P. Kim Liên, Q. Đống Đa, TP. Hà Nội",
        "licenseClass": "B2", "dateOfIssue": "2023-01-17", "dateOfExpiry": "2033-01-17",
    },
    "gplx_pet__thuy-giang-180": {  # XOAY 180°: watermark cạnh tên + nhãn dính "sinhDate"
        "_type": "gplx_pet",
        "idNumber": "011231007240",  # 1 chữ số OCR sai (xoay) — logic vẫn đúng
        "fullName": "NGUYỄN THỦY GIANG", "dateOfBirth": "1992-09-24",
        "nationality": "VIỆT NAM",
        "placeOfResidence": "P29 B12, TT Kim Liên P. Kim Liên, Qu Đống Đa, TP. Hà Nội",
        "licenseClass": "B2", "dateOfIssue": "2023-01-17", "dateOfExpiry": "2033-01-17",
    },
}


class _FixtureOcr:
    def __init__(self, lines):
        self._lines = lines

    def recognize(self, image):
        return list(self._lines)


def _load_lines(stem):
    data = json.loads((FIX / f"{stem}.json").read_text(encoding="utf-8"))
    return [OcrLine(**ln) for ln in data["lines"]]


@pytest.fixture(scope="module")
def plugins():
    pm = PluginManager(settings.plugins_dir)
    pm.load_all()
    return pm


@pytest.mark.parametrize("stem", list(GOLDEN))
def test_golden_extraction(plugins, stem):
    fx = FIX / f"{stem}.json"
    if not fx.exists():
        pytest.skip(f"thiếu fixture: {fx} (chạy tools/capture_ocr.py)")

    engine = PipelineEngine(
        plugins=plugins,
        quality=StubQualityChecker(),
        detector=StubDetector(),
        rectifier=StubRectifier(),
        classifier=RuleClassifier(plugins),
        structured=StubStructuredReader(),
        ocr=_FixtureOcr(_load_lines(stem)),
        extractor=LabelAnchoredExtractor(),
    )
    resp = engine.run(str(uuid.uuid4()), image=None)

    exp = GOLDEN[stem]
    assert resp.documentType == exp["_type"], f"{stem}: documentType"
    for field, value in exp.items():
        if field == "_type":
            continue
        assert resp.fields[field].value == value, f"{stem}:{field}"
