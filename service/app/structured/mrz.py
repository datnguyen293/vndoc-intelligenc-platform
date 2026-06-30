"""Parse MRZ (Machine Readable Zone) — ICAO 9303. THUẦN chuỗi, test được không cần ảnh.

Hiện hỗ trợ TD1 (Căn cước 2024 mặt sau, 3 dòng × 30 ký tự). MRZ tự chứa check digit
→ verify được tính đúng đắn (structured-data-first đáng tin hơn OCR). Tên trong MRZ
KHÔNG dấu → fullName chỉ là fallback (tên có dấu lấy từ mặt trước).
"""
from __future__ import annotations

import re

_VALUES = {**{str(d): d for d in range(10)},
           **{chr(ord("A") + i): 10 + i for i in range(26)}, "<": 0}
_WEIGHTS = (7, 3, 1)


def _check_digit(s: str) -> str:
    """Check digit ICAO 9303 (trọng số 7-3-1)."""
    total = sum(_VALUES.get(c, 0) * _WEIGHTS[i % 3] for i, c in enumerate(s))
    return str(total % 10)


def _yymmdd_to_slash(s: str, *, expiry: bool = False) -> str | None:
    """yyMMdd → dd/MM/yyyy. Suy thế kỷ: hạn dùng luôn 20yy; ngày sinh 20yy nếu yy<=30,
    ngược lại 19yy (đủ dùng cho dân CCCD)."""
    if not re.fullmatch(r"\d{6}", s):
        return None
    yy, mm, dd = int(s[0:2]), s[2:4], s[4:6]
    century = 2000 if (expiry or yy <= 30) else 1900
    return f"{dd}/{mm}/{century + yy:04d}"


def _name(line3: str) -> str:
    """Dòng tên TD1: 'HỌ<<TÊN' (ngăn họ/tên bằng '<<', từ trong tên bằng '<')."""
    surname, _, given = line3.partition("<<")
    surname = surname.replace("<", " ").strip()
    given = given.replace("<", " ").strip()
    return f"{surname} {given}".strip()


def parse_mrz_td1(lines: list[str]) -> dict[str, str]:
    """Parse MRZ TD1 (3 dòng × 30). Trả {field: value}; ngày dạng dd/MM/yyyy.

    Bố cục (ICAO 9303 TD1):
      L1: [0:2] loại  [2:5] quốc gia  [5:14] số thẻ  [14] cd  [15:30] optional (chứa số định danh 12 số)
      L2: [0:6] ngày sinh  [6] cd  [7] giới tính  [8:14] hạn  [14] cd  [15:18] quốc tịch
      L3: họ tên (không dấu)
    """
    if len(lines) < 3:
        return {}
    l1, l2, l3 = (re.sub(r"\s+", "", ln).upper() for ln in lines[:3])
    out: dict[str, str] = {}

    if len(l1) >= 15:
        doc_num = l1[5:14].replace("<", "")
        if doc_num:
            out["documentNumber"] = doc_num
        m = re.search(r"\d{12}", l1[15:])          # số định danh cá nhân nằm trong optional
        if m:
            out["idNumber"] = m.group(0)

    if len(l2) >= 15:
        dob = _yymmdd_to_slash(l2[0:6])
        if dob:
            out["dateOfBirth"] = dob
        sex = l2[7] if len(l2) > 7 else ""
        if sex in ("M", "F"):
            out["sex"] = "Nam" if sex == "M" else "Nữ"
        exp = _yymmdd_to_slash(l2[8:14], expiry=True)
        if exp:
            out["dateOfExpiry"] = exp
        nat = l2[15:18] if len(l2) >= 18 else ""
        if nat == "VNM":
            out["nationality"] = "Việt Nam"

    name = _name(l3)
    if name:
        out["fullName"] = name

    return out


def mrz_td1_checksums_ok(lines: list[str]) -> bool:
    """Verify 3 check digit chính của TD1 (số thẻ, ngày sinh, hạn dùng)."""
    if len(lines) < 2:
        return False
    l1, l2 = (re.sub(r"\s+", "", ln).upper() for ln in lines[:2])
    if len(l1) < 15 or len(l2) < 15:
        return False
    return (
        _check_digit(l1[5:14]) == l1[14]
        and _check_digit(l2[0:6]) == l2[6]
        and _check_digit(l2[8:14]) == l2[14]
    )


def find_mrz_td1(texts: list[str]) -> list[str] | None:
    """Tìm 3 dòng MRZ TD1 trong danh sách text OCR (mỗi dòng ~30 ký tự [A-Z0-9<],
    có '<'). Trả 3 dòng hoặc None."""
    cands = []
    for t in texts:
        s = re.sub(r"\s+", "", t).upper()
        if 25 <= len(s) <= 36 and "<" in s and re.fullmatch(r"[A-Z0-9<]+", s):
            cands.append(s)
    return cands[:3] if len(cands) >= 3 else None
