"""Phân tích ngày tháng tiếng Việt → ISO `YYYY-MM-DD` (DOC-08 §2)."""
from __future__ import annotations

import re

# dd<sep>mm<sep>yyyy — sep là bất kỳ tổ hợp space/-/./ (OCR render dấu không nhất quán,
# vd "24 - 09 1992", "19 05 - 2023", "24-09-1992")
_DMY = re.compile(r"(\d{1,2})[\s\-/.]+(\d{1,2})[\s\-/.]+(\d{4})")
# "ngày 07 tháng 11 năm 2024" và bản song ngữ "ngày/date 19 tháng/month 12 năm/year 2012".
# `\D{0,10}` cho phép chữ chèn giữa từ khóa và số (/date, /month, /year) + OCR dính chữ.
_PHRASE = re.compile(
    r"ng[àa]y\D{0,10}?([0-9liIoO]{1,2})\D{0,10}?th[áa]ng\D{0,10}?([0-9liIoO]{1,2})"
    r"\D{0,10}?n[ăa]m\D{0,10}?(\d{4})",
    re.IGNORECASE,
)
_DIGIT_FIX = str.maketrans({"l": "1", "I": "1", "i": "1", "o": "0", "O": "0"})


def _int(s: str) -> int:
    return int(s.translate(_DIGIT_FIX))


# Nới lỏng: "DD <có CHỮ> MM <...> YYYY" — chịu OCR hỏng từ khóa ("ngawdate", "máng").
# BẮT BUỘC có chữ giữa DD và MM → KHÔNG khớp ngày compact dd/mm/yyyy (ngày sinh, hết hạn).
_PHRASE_LOOSE = re.compile(
    r"\b([0-9liIoO]{1,2})\D*?[A-Za-zÀ-ỹ]\D*?([0-9liIoO]{1,2})\D*?(\d{4})\b"
)


def _iso(d: int, m: int, y: int) -> str | None:
    if 1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
        return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def find_date(text: str) -> str | None:
    """Tìm cụm ngày dd/mm/yyyy đầu tiên trong text → ISO."""
    m = _DMY.search(text)
    if m:
        return _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def find_date_phrase(text: str) -> str | None:
    """Tìm cụm ngày dạng câu → ISO. Ưu tiên chuẩn 'ngày..tháng..năm', rồi nới lỏng
    (chịu OCR hỏng từ khóa) — bản nới lỏng đòi có CHỮ giữa các số nên không nhầm
    ngày compact dd/mm/yyyy."""
    m = _PHRASE.search(text)
    if not m:
        m = _PHRASE_LOOSE.search(text)
    if m:
        return _iso(_int(m.group(1)), _int(m.group(2)), int(m.group(3)))
    return None


def to_iso(text: str) -> str | None:
    """Chuẩn hóa bất kỳ dạng ngày nào → ISO; None nếu không nhận dạng được."""
    return find_date(text) or find_date_phrase(text)
