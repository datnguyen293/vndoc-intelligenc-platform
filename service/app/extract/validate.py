"""Validate + business checks cho từng trường (DOC-08 §3, §4)."""
from __future__ import annotations

import re
from datetime import date

from app.plugins.contract import FieldSpec


def validate_field(value: str | None, spec: FieldSpec) -> list[str]:
    """Trả danh sách cảnh báo (rỗng = hợp lệ). Không chặn — giữ giá trị (DEC-032)."""
    warns: list[str] = []
    if value is None or value == "":
        if spec.required:
            warns.append(f"{spec.name}_thieu")
        return warns

    rules = spec.validate
    rgx = rules.get("regex")
    if rgx and not re.fullmatch(rgx, value):
        warns.append(f"{spec.name}_sai_dinh_dang")
    min_len = rules.get("minLen")
    if min_len and len(value) < min_len:
        warns.append(f"{spec.name}_qua_ngan")
    enum = rules.get("enum")
    if enum and value not in enum:
        warns.append(f"{spec.name}_ngoai_danh_muc")
    return warns


_OPS = {
    "<": lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    ">": lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
}


def cross_field_checks(fields: dict, checks: list) -> list[str]:
    """Kiểm tra quan hệ logic giữa các trường NGÀY (vd vào Đảng ≤ chính thức).

    `checks` = [[fieldA, op, fieldB], ...]; op ∈ {<,<=,>,>=}. Chỉ chạy khi cả hai
    trường có giá trị ISO hợp lệ. Sai → cảnh báo (không chặn — DEC-032).
    """
    warns: list[str] = []
    for chk in checks:
        if not isinstance(chk, (list, tuple)) or len(chk) != 3:
            continue
        a, op, b = chk
        fa, fb = fields.get(a), fields.get(b)
        if not fa or not fb or not fa.value or not fb.value:
            continue
        try:
            da, db = date.fromisoformat(fa.value), date.fromisoformat(fb.value)
        except ValueError:
            continue
        fn = _OPS.get(op)
        if fn and not fn(da, db):
            warns.append(f"thu_tu_ngay_sai:{a}{op}{b}")
    return warns


def run_checks(value: str | None, spec: FieldSpec) -> list[str]:
    """Rule nghiệp vụ (vd hết hạn). Cần value đã chuẩn hóa ISO cho ngày."""
    warns: list[str] = []
    if not value:
        return warns
    if "warn_if_expired" in spec.checks:
        try:
            if date.fromisoformat(value) < date.today():
                warns.append("da_het_han")
        except ValueError:
            pass
    return warns
