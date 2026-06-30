"""Tiện ích chuỗi dùng chung cho match nhãn & phân loại (bền với OCR mất dấu)."""
from __future__ import annotations

import re
import unicodedata


def fold(s: str) -> str:
    """Bỏ dấu tiếng Việt + casefold (đ→d). Dùng để SO KHỚP, không đổi giá trị gốc."""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.casefold()


def clean_token(t: str) -> str:
    """Token đã fold, bỏ ký tự không phải chữ-số (vd 'Số'→'so', 'tên:'→'ten')."""
    return re.sub(r"[^0-9a-z]", "", fold(t))


def key(s: str) -> str:
    """Khóa so khớp: fold + bỏ khoảng trắng + bỏ ký tự lạ (vd 'Họ và tên'→'hovaten')."""
    return "".join(clean_token(t) for t in s.split())
