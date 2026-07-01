"""Unit test parser QR BHYT — THUẦN chuỗi, KHÔNG cần ảnh/model → nhanh, tất định.

Payload lấy nguyên văn từ QR ảnh mẫu thật (samples/bhyt/tien-dat.jpeg) đã giải mã.
"""
from app.structured.qr import _hex_to_text, parse_bhyt_qr

# QR thật của thẻ BHYT mẫu (ngăn '|'); trường [1],[15] mã hoá HEX của UTF-8.
REAL_QR = (
    "0111077012|4e677579e1bb856e205469e1babf6e20c490e1baa174|29/03/1988|1|-|"
    "01 - C54|01/07/2023|-|31/07/2023|01050111077012|-|4| 01/10/2027|"
    "4641c59ff02659c3-1202|4|"
    "5175e1baad6e2043e1baa775204769e1baa5792c205468c3a06e68207068e1bb912048c3a0204ee1bb9969|$"
)


def test_parse_real_qr_all_fields():
    d = parse_bhyt_qr(REAL_QR)
    assert d["idNumber"] == "0111077012"
    assert d["fullName"] == "Nguyễn Tiến Đạt"          # giải HEX UTF-8
    assert d["dateOfBirth"] == "29/03/1988"            # raw dd/MM/yyyy
    assert d["sex"] == "Nam"                           # mã '1' -> Nam
    assert d["objectCode"] == "01 - C54"
    assert d["validFrom"] == "01/07/2023"
    assert d["dateOfIssue"] == "31/07/2023"
    assert d["fiveYearContinuous"] == "01/10/2027"     # bỏ khoảng trắng đầu
    assert d["issuePlace"] == "Quận Cầu Giấy, Thành phố Hà Nội"


def test_hex_to_text():
    assert _hex_to_text("4e677579e1bb856e") == "Nguyễn"  # 'Nguyễn'
    assert _hex_to_text("zzzz") is None                   # không phải hex
    assert _hex_to_text("abc") is None                    # độ dài lẻ


def test_empty_and_garbage():
    assert parse_bhyt_qr("") == {}
    assert parse_bhyt_qr("khong-phai-qr") == {}           # idNumber sai regex -> bỏ


def test_dash_placeholders_dropped():
    # '-' là placeholder rỗng → không tạo trường.
    d = parse_bhyt_qr("0111077012|-|-|-|-|-|-|-|-")
    assert d == {"idNumber": "0111077012"}


def test_female_code():
    d = parse_bhyt_qr("0111077012||29/03/1988|2")
    assert d["sex"] == "Nữ"


# QR thẻ BHYT MẪU CŨ: mã số 15 ký tự (2 chữ + 13 số); trường [4] = địa chỉ (HEX).
QR_OLD = (
    "HS4010120878837|56c5a9205875c3a26e204d696e68|07/09/2008|1|"
    "5068c6b0e1bb9d6e67204e6768c4a96120c490c3b42c205175e1baad6e2043e1baa775204769e1baa5792c"
    "205468c3a06e68207068e1bb912048c3a0204ee1bb9969|01 - 028|24/01/2019|-|24/01/2019|$"
)


def test_parse_old_15char_code():
    d = parse_bhyt_qr(QR_OLD)
    assert d["idNumber"] == "HS4010120878837"            # 2 chữ + 13 số
    assert d["fullName"] == "Vũ Xuân Minh"
    assert d["dateOfBirth"] == "07/09/2008"
    assert d["sex"] == "Nam"
    assert d["placeOfResidence"] == "Phường Nghĩa Đô, Quận Cầu Giấy, Thành phố Hà Nội"
    assert d["objectCode"] == "01 - 028"
