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
    # MẪU MỚI (ngoc-hung): số thẻ 12 chữ số, tên KHÔNG nhãn (vi_name_orphan), nhãn "Ngày sinh"
    # /"Ngày vào Đảng"/"Ngày cấp:". placeOfOrigin & officialDate KHÔNG có trên mẫu này (=None).
    # partyOrganization CỤT "Đằng Bộ" (mất "Công An Trung Ương" do _MERGE_CAP=1) — khoá nguyên trạng.
    "the_dang_vien__ngoc-hung": {
        "_type": "the_dang_vien",
        "cardNumber": "001088023765", "fullName": "NGUYỄN NGỌC HỨNG",
        "dateOfBirth": "1988-02-13", "partyJoinDate": "2011-06-14",
        "partyOrganization": "Đằng Bộ", "dateOfIssue": "2025-09-14",
        "placeOfOrigin": None, "officialDate": None,
    },
    "the_dang_vien__ngoc-hung-270": {  # XOAY 270° — khoá nắn hướng + trích xuất mẫu mới
        "_type": "the_dang_vien",
        "cardNumber": "001088023765", "fullName": "NGUYỄN NGỌC HƯNG",
        "dateOfBirth": "1988-02-13", "partyJoinDate": "2011-06-14",
        "partyOrganization": "Đảng Bộ", "dateOfIssue": "2025-09-14",
        "placeOfOrigin": None, "officialDate": None,
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
    "bhyt__tien-dat": {  # BHYT đường OCR FALLBACK (QR hỏng). QR-first là đường chính.
        "_type": "bhyt",
        # OCR ra "1855 0111077012" (dính tiền tố nhiễu); _pattern_fallback bắt token
        # 10 số → idNumber đúng kể cả khi mất nhãn "Mã số".
        "idNumber": "0111077012",
        "fullName": "NGUYỄN TIẾN ĐẠT", "dateOfBirth": "1988-03-29", "sex": "Nam",
        "registeredHospital": "Trạm Y tế phường Láng Thượng (TTYT Đống",  # wrap "Đa)" rớt
        "validFrom": "2023-07-01", "fiveYearContinuous": "2027-10-01",
        "dateOfIssue": "2023-07-31",
    },
    "bhyt__manh-hung": {  # Golden = đường OCR-only (StubStructured): mã số OCR hỏng → null.
        "_type": "bhyt",  # PRODUCTION: QR nhỏ được phóng to (~4×) → idNumber=0132790125
        "idNumber": None,  # (xem test_small_qr_upscale_recovers_idnumber).
        "fullName": "NGUYỄN MẠNH HÙNG", "dateOfBirth": "2024-12-23", "sex": "Nam",
        "validFrom": "2024-12-23", "fiveYearContinuous": "2029-12-23",
        "dateOfIssue": "2025-03-28",
    },
    "bhyt__thuy-giang": {  # BHYT MẪU MỚI (ảnh khác cùng người), có benefitLevel
        "_type": "bhyt",
        "fullName": "NGUYỄN MẠNH HÙNG", "dateOfBirth": "2024-12-23", "sex": "Nam",
        "benefitLevel": "1",
        "validFrom": "2024-12-23", "fiveYearContinuous": "2029-12-23",
        "dateOfIssue": "2025-03-28",
    },
    "cmnd_12__thuy-giang": {  # cmnd_12 biến thể "CHỨNG MINH NHÂN DÂN" (cũ)
        "_type": "cmnd_12",
        "idNumber": "001192004768", "fullName": "NGUYỄN THÙY GIANG",
        "dateOfBirth": "1992-09-24", "sex": "Nữ",
        "placeOfOrigin": "Tân Triều, Thanh Trì, Hà Nội",
        "dateOfExpiry": "2030-11-04",
    },
    "cmnd_12__anh-hoang": {  # cmnd_12 biến thể "CĂN CƯỚC CÔNG DÂN" 12 số (mã vạch, không QR)
        "_type": "cmnd_12", "_hint": "cmnd",   # trùng title cccd_chip_front → cần hint họ
        "idNumber": "031091006890", "fullName": "NGUYỄN ANH HOÀNG",
        "dateOfBirth": "1991-09-09", "sex": "Nam", "nationality": "Việt Nam",
        "placeOfOrigin": "Ngũ Phúc, Kiến Thuy Hải Phòng",
        "placeOfResidence": "1 92 Lê Thánh Tông Máy Chai, Ngô Quyền, Hải Phòng",
        "dateOfExpiry": "2031-09-09",
    },
    "cmnd_12__quoc-phuong": {  # cmnd_12 biến thể "CĂN CƯỚC CÔNG DÂN" 12 số (mã vạch)
        "_type": "cmnd_12", "_hint": "cmnd",
        "idNumber": "001202017557", "fullName": "PHẠM QUỐC PHƯƠNG",
        "dateOfBirth": "2002-01-17", "sex": "Nam", "nationality": "Việt Nam",
        "placeOfOrigin": "Hà Nội",
        "placeOfResidence": "30 Phùng Khắc Khoan Ngô Thì Nhậm, Hai Bà Trưng, Hà Nội",
        "dateOfExpiry": "2030-08-15",
    },
    "cmnd_9__tien-dat": {  # CMND 9 số (giấy cũ ép nhựa) — số mực đỏ OCR ra rác (null).
        "_type": "cmnd_9",  # Tên + Ngày sinh + Thường trú (đã gỡ nhãn "thường trú" dính)
        "fullName": "NGUYỄN TIẾN ĐẠT",  # + Nguyên quán (orphan, một phần do OCR rớt "Lam Cốt").
        "dateOfBirth": "1988-03-29",
        "placeOfResidence": "Tân Lập Lam Cốt, Tân Yên, Bắc Giang",
        "placeOfOrigin": "Tân Yên Bắc Giang",
    },
    "cmnd_9__bao-duy": {  # ảnh rõ → đọc đủ 5 trường (số 9 sạch sau digitsOnly)
        "_type": "cmnd_9",
        "idNumber": "020016298", "fullName": "THÁI BẢO DUY",
        "dateOfBirth": "1994-04-30",
        "placeOfOrigin": "TP. Hồ Chí Minh",
        "placeOfResidence": "18 Lê Văn Lương Phước Kiểng, Nhà Bè, TP. Hồ Chí Minh",
    },
    "cmnd_9__bao-ngoc": {  # 'THUYỄN' là lỗi OCR cố hữu (đóng băng)
        "_type": "cmnd_9",
        "idNumber": "145064321", "fullName": "THUYỄN BẢO NGỌC",
        "dateOfBirth": "1983-09-07",
        "placeOfOrigin": "Khoái Châu, Hưng Yên",
        "placeOfResidence": "Bình Minh Khoái Châu, Hưng Yên",
    },
    "cmnd_9__ngoc-chi": {
        "_type": "cmnd_9",
        "idNumber": "023806188", "fullName": "TRẦN NGỌC TRÍ",
        "dateOfBirth": "1985-02-08",
        "placeOfOrigin": "TP. Hồ Chí Minh",
        "placeOfResidence": "254 33 40 Bến Vân Đồn, Phường 5, Q4, TP. Hồ Chí Minh",
    },
    "cmnd_9__thu-huong": {
        "_type": "cmnd_9",
        "idNumber": "206207791", "fullName": "TRƯƠNG THỊ THU HƯƠNG",
        "dateOfBirth": "1998-09-30",
        "placeOfOrigin": "Thăng Bình, Quảng Nam",
        "placeOfResidence": "1 Bình Triều, Thăng Bình, Quảng Nam",
    },
    "cccd_chip_front__tien-dat": {  # đường OCR-only (golden dùng StubStructured);
        "_type": "cccd_chip_front",  # prod: QR điền idNumber/sex/dateOfIssue/oldIdNumber
        "idNumber": "024088010438", "fullName": "NGUYỄN TIẾN ĐẠT",
        "dateOfBirth": "1988-03-29",
        "placeOfResidence": "Lam Cốt, Tân Yên, Bắc Giang",
        "dateOfExpiry": "2028-03-29",
    },
    "cccd_2024_front__dinh-nam": {  # Căn cước mới mặt trước — OCR thuần (không QR mặt trước)
        "_type": "cccd_2024_front",
        "idNumber": "026099003333", "fullName": "LƯƠNG ĐÌNH NAM",
        "dateOfBirth": "1999-12-30", "nationality": "Việt Nam",
    },
    "cccd_2024_back__dinh-nam": {  # OCR-only; prod: QR điền idNumber/fullName/dob/sex
        "_type": "cccd_2024_back",
        "placeOfBirth": "Tân Phú, Vĩnh Tường, Vĩnh Phúc",
        "dateOfIssue": "2024-08-01", "dateOfExpiry": "2039-12-30",
    },
    "passport_vn__cu": {  # hộ chiếu CŨ ("Họ và tên" + Số GCMND 9 số). MRZ OCR hỏng → VIZ bù.
        "_type": "passport_vn",
        "idNumber": "B7849474", "fullName": "NGUYỄN TIẾN ĐẠT",
        "nationality": "VIỆT NAM", "dateOfBirth": "1988-03-29", "sex": "Nam",
        "placeOfBirth": "BẮC GIANG", "personalIdNumber": "121647952",
        "dateOfIssue": "2013-05-13", "dateOfExpiry": "2023-05-13",
        "issuedBy": "Cục Quản lý xuất nhập cảnh",
    },
    "passport_vn__moi": {  # hộ chiếu MỚI (e-passport, tách họ/tên, Số ĐDCN 12 số)
        "_type": "passport_vn",
        "idNumber": "E01828939", "surname": "NGUYỄN", "givenNames": "TIẾN ĐẠT",
        "fullName": "NGUYỄN TIẾN ĐẠT", "nationality": "VIỆT NAM",
        "dateOfBirth": "1988-03-29", "sex": "Nam", "placeOfBirth": "Bắc Giang",
        "personalIdNumber": "024088010438",
        "dateOfIssue": "2024-05-20", "dateOfExpiry": "2034-05-20",
    },
    "the_quan_nhan__phan-van-trung": {  # Chứng minh quân nhân chuyên nghiệp (ảnh nhỏ)
        "_type": "the_quan_nhan",
        "idNumber": "438910546888", "fullName": "PHAN VĂN TRUNG",
        "dateOfBirth": "1989-03-18", "unit": "TỔNG CỤC HẬU CẦN",
    },
    "the_quan_nhan__the-quan-nhan": {  # ảnh 350x200 rất nhỏ: tên nhoè (null), còn lại ổn
        "_type": "the_quan_nhan",
        "idNumber": "549201042187", "dateOfBirth": "1992-04-19",
        "unit": "Tổng cực Kỹ thuật", "dateOfIssue": "2019-10-01",
        "dateOfExpiry": "9 2031",
    },
    # BIẾN THỂ SĨ QUAN (cuong): số 8 số, layout 2 cột (right_of_label), có rank "Cấp úy",
    # KHÔNG có ngày sinh (dateOfBirth=null đúng). dateOfIssue ngày "16" là OCR đọc nhầm "10"
    # do loá — khoá nguyên trạng OCR (test bộ trích xuất, không phải độ chính xác OCR).
    "the_quan_nhan__cuong": {
        "_type": "the_quan_nhan",
        "idNumber": "20056913", "fullName": "TRẦN QUỐC CƯỜNG",
        "dateOfBirth": None, "rank": "Cấp úy", "unit": "Bộ đội Biên phòng",
        "dateOfIssue": "2022-02-16", "dateOfExpiry": "12/2034",
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
    exp = GOLDEN[stem]
    # _hint: hint thô họ (cmnd/cccd) như client gửi — cần cho loại nhập nhằng title
    # (vd "CĂN CƯỚC CÔNG DÂN" 12 số mã vạch là cmnd_12 nhưng trùng title cccd_chip_front).
    resp = engine.run(str(uuid.uuid4()), image=None, doc_type_hint=exp.get("_hint"))

    assert resp.documentType == exp["_type"], f"{stem}: documentType"
    for field, value in exp.items():
        if field in ("_type", "_hint"):
            continue
        assert resp.fields[field].value == value, f"{stem}:{field}"
