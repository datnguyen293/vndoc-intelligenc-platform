"""Unit test cho các hàm chuẩn hóa (DOC-08 §2)."""
from app.extract.dates import to_iso
from app.extract.normalize import dot_separator, norm_sex


def test_dot_separator_forces_dot():
    # Số thẻ luôn 'xx.xxxxxx' → mọi dấu phân cách lạ ép về '.'
    assert dot_separator("40:140050") == "40.140050"
    assert dot_separator("40 140050") == "40.140050"
    assert dot_separator("83,060977") == "83.060977"
    assert dot_separator("83.060977") == "83.060977"  # đã đúng → giữ nguyên


def test_to_iso_handles_mixed_separators():
    # VietOCR render dấu phân cách ngày không nhất quán
    assert to_iso("24 - 09 - 1992") == "1992-09-24"
    assert to_iso("24 - 09 1992") == "1992-09-24"
    assert to_iso("19 05 - 2023") == "2023-05-19"
    assert to_iso("Ngày 07 tháng 11 năm 2024") == "2024-11-07"
    assert to_iso("Ngay 07 thang 1lnam 2008") == "2008-11-07"  # OCR dính chữ + 1↔l


def test_norm_sex():
    assert norm_sex("NAM") == "Nam"
    assert norm_sex("nữ") == "Nữ"
