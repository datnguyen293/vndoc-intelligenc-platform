"""Unit test parser MRZ TD3 (hộ chiếu) — THUẦN chuỗi. MRZ lấy từ docs/samples/ho-chieu-*."""
from app.structured.mrz import find_mrz_td3, mrz_td3_checksums_ok, parse_mrz_td3

# Hộ chiếu CŨ (#01): số GCMND 9 số, số hộ chiếu 1 chữ + 7 số.
MRZ_OLD = [
    "P<VNMNGUYEN<<TIEN<DAT<<<<<<<<<<<<<<<<<<<<<<<<<",
    "B7849474<6VNM8803296M2305134121647952<<<<<50",
]
# Hộ chiếu MỚI (#02, e-passport): số ĐDCN 12 số, số hộ chiếu 1 chữ + 8 số.
MRZ_NEW = [
    "P<VNMNGUYEN<<TIEN<DAT<<<<<<<<<<<<<<<<<<<<<<<<<",
    "E018289390VNM8803296M3405204024088010438<<08",
]


def test_parse_old():
    d = parse_mrz_td3(MRZ_OLD)
    assert d["idNumber"] == "B7849474"
    assert d["nationality"] == "Việt Nam"
    assert d["dateOfBirth"] == "29/03/1988"
    assert d["sex"] == "Nam"
    assert d["dateOfExpiry"] == "13/05/2023"
    assert d["personalIdNumber"] == "121647952"      # số GCMND 9 số


def test_parse_new():
    d = parse_mrz_td3(MRZ_NEW)
    assert d["idNumber"] == "E01828939"
    assert d["dateOfBirth"] == "29/03/1988"
    assert d["sex"] == "Nam"
    assert d["dateOfExpiry"] == "20/05/2034"
    assert d["personalIdNumber"] == "024088010438"   # số ĐDCN 12 số
    assert "fullName" not in d                        # tên không lấy từ MRZ (không dấu)


def test_checksums_ok():
    assert mrz_td3_checksums_ok(MRZ_OLD) is True
    assert mrz_td3_checksums_ok(MRZ_NEW) is True
    bad = [MRZ_NEW[0], "E018289399VNM8803296M3405204024088010438<<08"]  # cd số HC sai
    assert mrz_td3_checksums_ok(bad) is False


def test_find_in_ocr():
    noise = ["HỘ CHIẾU / PASSPORT", *MRZ_NEW, "20/05/2034"]
    assert find_mrz_td3(noise) == MRZ_NEW
