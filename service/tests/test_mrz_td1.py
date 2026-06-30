"""Unit test parser MRZ TD1 — THUẦN chuỗi. MRZ lấy từ ảnh Căn cước mặt sau thật."""
from app.structured.mrz import (
    find_mrz_td1,
    mrz_td1_checksums_ok,
    parse_mrz_td1,
)

# MRZ TD1 thật (Lương Đình Nam) — Căn cước 2024 mặt sau.
MRZ = [
    "IDVNM0990033332026099003333<<4",
    "9912304M3912302VNM<<<<<<<<<<<2",
    "LUONG<<DINH<NAM<<<<<<<<<<<<<<<",
]


def test_parse_td1():
    d = parse_mrz_td1(MRZ)
    assert d["idNumber"] == "026099003333"        # số định danh 12 số trong optional
    assert d["documentNumber"] == "099003333"
    assert d["dateOfBirth"] == "30/12/1999"
    assert d["sex"] == "Nam"
    assert d["dateOfExpiry"] == "30/12/2039"
    assert d["nationality"] == "Việt Nam"
    assert d["fullName"] == "LUONG DINH NAM"       # không dấu (MRZ)


def test_checksums_ok():
    assert mrz_td1_checksums_ok(MRZ) is True
    bad = [MRZ[0], "9912304M3912309VNM<<<<<<<<<<<2", MRZ[2]]  # cd hạn dùng [14] sai
    assert mrz_td1_checksums_ok(bad) is False


def test_find_in_ocr_text():
    noise = ["Nơi cư trú", "BỘ CÔNG AN", *MRZ, "30/12/2039"]
    found = find_mrz_td1(noise)
    assert found == MRZ


def test_too_few_lines():
    assert parse_mrz_td1(["IDVNM..."]) == {}
