"""Unit test cho các hàm chuẩn hóa (DOC-08 §2)."""
from app.extract.dates import to_iso
from app.extract.normalize import (
    digits_only,
    dot_separator,
    norm_sex,
    strip_residence_label_echo,
)


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


def test_digits_only():
    assert digits_only('""020016298') == "020016298"   # OCR thêm dấu nháy quanh số
    assert digits_only("024088010438") == "024088010438"
    assert digits_only("1 No 024") == "1024"            # gộp số dính (sau đó fallback token lo)


def test_strip_residence_label_echo():
    # "thường trú" OCR sai thành "Tưưng Trị" dính đầu địa chỉ → gỡ, GIỮ địa danh thật.
    assert strip_residence_label_echo(
        "Tưưng Trị Tân Lập Lam Cốt, Tân Yên, Bắc Giang"
    ) == "Tân Lập Lam Cốt, Tân Yên, Bắc Giang"
    # KHÔNG nuốt nhầm "Tân" (~ "đăng" lev2) khi không có nhãn dính.
    assert strip_residence_label_echo("Tân Lập, Lam Cốt") == "Tân Lập, Lam Cốt"
    # Gỡ hết (toàn từ nhãn) → giữ nguyên cho an toàn.
    assert strip_residence_label_echo("Thường trú") == "Thường trú"
