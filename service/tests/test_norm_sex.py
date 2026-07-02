"""norm_sex phải bóc đúng Nam/Nữ khỏi giá trị lẫn nhãn/nhiễu, tránh bẫy 'Việt Nam'."""
from __future__ import annotations

import pytest

from app.extract.normalize import norm_sex, sex_from_cccd


@pytest.mark.parametrize("raw,expected", [
    ("Nam", "Nam"),
    ("Nữ", "Nữ"),
    ("NAM / M", "Nam"),                                   # hộ chiếu song ngữ
    ("Nữ / F", "Nữ"),
    ("1 Sex Nam Quốc tịch Nationally Việt Nam", "Nam"),   # thẻ chip: gộp nguyên dòng
    ("Sex Nữ Quốc tịch Việt Nam", "Nữ"),                 # nữ + có 'Việt Nam' phía sau
    ("Sox", ""),                                          # OCR đọc lệch 'Sex' → rỗng, KHÔNG sai
    ("Việt Nam", ""),                                     # chỉ có quốc tịch → KHÔNG nhận nhầm Nam
    ("", ""),
])
def test_norm_sex(raw, expected):
    assert norm_sex(raw) == expected


@pytest.mark.parametrize("id12,expected", [
    ("001201033179", "Nam"),   # chữ số thứ 4 = 2 (chẵn, TK21) → Nam (trung-hieu, sinh 2001)
    ("026099003333", "Nam"),   # thứ 4 = 0 (chẵn, TK20) → Nam (dinh-nam)
    ("024088010438", "Nam"),   # thứ 4 = 0 → Nam (tien-dat)
    ("001301033179", "Nữ"),    # thứ 4 = 3 (lẻ, TK21) → Nữ
    ("001101033179", "Nữ"),    # thứ 4 = 1 (lẻ, TK20) → Nữ
    ("02408801043", None),     # 11 số → không suy
    ("0240880104388", None),   # 13 số → không suy
    ("02408801043X", None),    # có chữ → không suy
    (None, None),
    ("", None),
])
def test_sex_from_cccd(id12, expected):
    assert sex_from_cccd(id12) == expected
