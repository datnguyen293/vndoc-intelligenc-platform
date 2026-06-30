"""Hàm chuẩn hóa giá trị trường (DOC-08 §2)."""
from __future__ import annotations

import re

from . import dates
from .textutil import clean_token


def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# Từ thuộc nhãn "Nơi ĐKHK thường trú" — dùng để gỡ phần nhãn bị OCR đọc sai dính vào
# đầu giá trị địa chỉ (vd "thường trú"→"Tưưng Trị" trên thẻ giấy ép cũ).
_RES_LABEL_ECHO = {"noi", "dkhk", "dang", "ky", "ho", "khau", "thuong", "tru"}

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


def strip_residence_label_echo(s: str) -> str:
    """Gỡ các TỪ ĐẦU là phần nhãn "Nơi ĐKHK thường trú" bị OCR đọc sai dính vào giá trị
    (khớp mờ: từ dài lev≤2, từ ngắn lev≤1). Dừng ở từ đầu tiên không phải nhãn → địa danh."""
    words = s.split()
    i = 0
    while i < len(words):
        w = clean_token(words[i])
        if not w:
            i += 1
            continue
        # "thường"→OCR hay sai nặng (cho lev≤2); các từ khác siết lev≤1 để KHỎI nuốt
        # nhầm địa danh thật (vd "Tân" ~ "đăng" lev2).
        hit = any(w == e or _lev(w, e) <= (2 if e == "thuong" else 1) for e in _RES_LABEL_ECHO)
        if not hit:
            break
        i += 1
    if i == 0 or i >= len(words):   # không gỡ gì, hoặc gỡ hết → giữ nguyên (an toàn)
        return s
    return " ".join(words[i:]).strip(" ,")


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
    "stripResidenceLabelEcho": strip_residence_label_echo,
    "dotSeparator": dot_separator,
    "stripEdgeNonDigits": strip_edge_nondigits,
}


def apply_normalizers(value: str, names: list[str]) -> str:
    for name in names:
        fn = NORMALIZERS.get(name)
        if fn:
            value = fn(value)
    return value
