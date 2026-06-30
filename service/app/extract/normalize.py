"""Hàm chuẩn hóa giá trị trường (DOC-08 §2)."""
from __future__ import annotations

import re

from . import dates

# Nhầm lẫn OCR thường gặp trong ngữ cảnh chữ số
_DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1",
                            "B": "8", "S": "5", "Z": "2"})


def trim(s: str) -> str:
    return s.strip()


def collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def remove_spaces(s: str) -> str:
    return re.sub(r"\s+", "", s)


def upper_vi(s: str) -> str:
    return s.upper()


def fix_digits(s: str) -> str:
    return s.translate(_DIGIT_FIX)


def strip_dots(s: str) -> str:
    s = re.sub(r"[·…]+", " ", s)
    s = re.sub(r"\.{2,}", " ", s)
    return collapse_spaces(s)


def norm_sex(s: str) -> str:
    t = s.strip().lower()
    if t in {"nam", "m", "male"}:
        return "Nam"
    if t in {"nữ", "nu", "f", "female"}:
        return "Nữ"
    return s.strip()


def to_iso_date(s: str) -> str:
    return dates.to_iso(s) or s


def dict_fix(s: str) -> str:
    # Placeholder: khớp gần đúng địa danh/dân tộc với dictionary (TODO khi có từ điển).
    return s


def dot_separator(s: str) -> str:
    """Mã dạng 'số.số' (vd số thẻ Đảng viên xx.xxxxxx): ép mọi dấu phân cách do OCR
    đọc nhầm (':', ',', ' ', ' - '...) về '.'."""
    return re.sub(r"(\d)[^\w]+(\d)", r"\1.\2", s.strip())


def strip_edge_nondigits(s: str) -> str:
    """Bỏ ký tự không-phải-số ở ĐẦU/CUỐI (vd OCR thêm '-' khi xoay → '-83.060977')."""
    return re.sub(r"^\D+|\D+$", "", s)


NORMALIZERS = {
    "trim": trim,
    "collapseSpaces": collapse_spaces,
    "removeSpaces": remove_spaces,
    "upperVi": upper_vi,
    "fixDigits": fix_digits,
    "stripDots": strip_dots,
    "normSex": norm_sex,
    "toIsoDate": to_iso_date,
    "dictFix": dict_fix,
    "dotSeparator": dot_separator,
    "stripEdgeNonDigits": strip_edge_nondigits,
}


def apply_normalizers(value: str, names: list[str]) -> str:
    for name in names:
        fn = NORMALIZERS.get(name)
        if fn:
            value = fn(value)
    return value
