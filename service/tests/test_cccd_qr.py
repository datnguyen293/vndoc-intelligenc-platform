"""Unit test parser QR CCCD/Căn cước — THUẦN chuỗi, KHÔNG cần ảnh/model.

Payload lấy nguyên văn từ QR ảnh mẫu thật đã giải mã:
- chip mặt trước (Nguyễn Tiến Đạt): có số CMND 9 số cũ.
- Căn cước mặt sau (Lương Đình Nam): trường số CMND cũ rỗng + thừa trường rỗng.
"""
from app.structured.qr import parse_cccd_qr

QR_CHIP_FRONT = "024088010438|121647952|Nguyễn Tiến Đạt|29031988|Nam|Tân Lập, Lam Cốt, Tân Yên, Bắc Giang|22062022"
QR_CC_BACK = "026099003333||Lương Đình Nam|30121999|Nam|Thôn Dẫn Tự, Tân Phú, Vĩnh Tường, Vĩnh Phúc|01082024||||"


def test_chip_front():
    d = parse_cccd_qr(QR_CHIP_FRONT)
    assert d["idNumber"] == "024088010438"
    assert d["oldIdNumber"] == "121647952"
    assert d["fullName"] == "Nguyễn Tiến Đạt"
    assert d["dateOfBirth"] == "29/03/1988"     # ddMMyyyy → dd/MM/yyyy
    assert d["sex"] == "Nam"
    assert d["placeOfResidence"] == "Tân Lập, Lam Cốt, Tân Yên, Bắc Giang"
    assert d["dateOfIssue"] == "22/06/2022"


def test_can_cuoc_back():
    d = parse_cccd_qr(QR_CC_BACK)
    assert d["idNumber"] == "026099003333"
    assert "oldIdNumber" not in d                # trường rỗng → bỏ
    assert d["fullName"] == "Lương Đình Nam"
    assert d["dateOfBirth"] == "30/12/1999"
    assert d["sex"] == "Nam"
    assert d["placeOfResidence"] == "Thôn Dẫn Tự, Tân Phú, Vĩnh Tường, Vĩnh Phúc"
    assert d["dateOfIssue"] == "01/08/2024"


def test_empty_and_garbage():
    assert parse_cccd_qr("") == {}
    assert parse_cccd_qr("abc|def") == {}        # idNumber sai → không nhận
