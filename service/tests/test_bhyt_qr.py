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
