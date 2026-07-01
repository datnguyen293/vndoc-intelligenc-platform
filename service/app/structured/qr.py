"""Đọc & parse QR (ADR-006 — structured-data-first).

- `decode_qr`: giải mã payload QR từ ảnh. Ưu tiên zxing-cpp (bền với xoay/nghiêng),
  fallback OpenCV. Import lib BÊN TRONG hàm để service vẫn chạy khi máy đích chưa cài
  (degrade an toàn: trả []).
- `parse_*`: chuyển payload chuỗi → {field: value} THUẦN (không cần ảnh) → test được
  độc lập với spec trong docs/samples.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger("dip.structured.qr")


def decode_qr(image, upscale: bool = False) -> list[str]:
    """Giải mã mọi QR trong ảnh → danh sách payload. Ảnh None / chưa cài lib / không có
    QR → []. `upscale`: nếu đọc native thất bại thì phóng to ảnh nhỏ rồi thử lại — CHỈ bật
    cho loại giấy tờ CÓ QR (BHYT/CCCD), tránh tốn thời gian cho loại không QR."""
    if image is None:
        return []
    payloads = _decode_zxing(image) or _decode_opencv(image)
    if payloads or not upscale:
        return payloads
    # Fallback QR NHỎ (chỉ khi upscale=True, SAU khi native fail): áp cho ảnh ĐỘ PHÂN GIẢI
    # THẤP (< _UPSCALE_MAX_SRC) — QR nhỏ + ít pixel, phóng to (nội suy) giúp zxing định vị
    # finder pattern (vd thẻ 589px, QR ~50px chỉ giải được khi phóng ~4× lên ~2400px). Ảnh
    # đủ lớn mà không giải được thì upscale KHÔNG thêm thông tin → bỏ qua.
    pil = _as_pil(image)
    if pil is None:
        return []
    w, h = pil.size
    longest = max(w, h)
    if longest >= _UPSCALE_MAX_SRC:
        return []
    for target in (2400, 3600):
        scale = target / longest
        up = pil.resize((round(w * scale), round(h * scale)))
        payloads = _decode_zxing(up)
        if payloads:
            return payloads
    return []


# Chỉ phóng to để cứu QR khi ảnh nguồn nhỏ hơn ngưỡng này (px). Ảnh lớn hơn đã ở res tối
# đa — upscale không giúp mà tốn thời gian (nhất là thẻ KHÔNG có QR: passport/CMND...).
_UPSCALE_MAX_SRC = 1500


def _as_pil(image):
    """Đưa ảnh (PIL hoặc numpy) về PIL để phóng to; None nếu không được."""
    if hasattr(image, "resize") and hasattr(image, "size"):
        return image
    try:
        import numpy as np
        from PIL import Image as _PILImage

        arr = np.asarray(image)
        if arr.ndim >= 2:
            return _PILImage.fromarray(arr)
    except Exception:  # noqa: BLE001
        return None
    return None


def _decode_zxing(image) -> list[str]:
    try:
        import zxingcpp
    except Exception:  # noqa: BLE001 — chưa cài → bỏ qua, thử backend khác
        return []
    try:
        results = zxingcpp.read_barcodes(image)
    except Exception as exc:  # noqa: BLE001
        log.warning("zxing-cpp đọc QR lỗi: %s", exc)
        return []
    return [r.text for r in results if getattr(r, "text", "")]


def _decode_opencv(image) -> list[str]:
    try:
        import cv2
        import numpy as np
    except Exception:  # noqa: BLE001
        return []
    try:
        arr = np.asarray(image)
        if arr.ndim == 3 and arr.shape[2] == 3:
            arr = arr[:, :, ::-1]  # PIL RGB → BGR cho OpenCV
        ok, infos, _pts, _ = cv2.QRCodeDetector().detectAndDecodeMulti(arr)
        return [t for t in infos if t] if ok else []
    except Exception as exc:  # noqa: BLE001
        log.warning("OpenCV đọc QR lỗi: %s", exc)
        return []


def _hex_to_text(s: str) -> str | None:
    """Một số trường QR BHYT mã hoá HEX của UTF-8 (vd '4e6775...'→'Nguyễn Tiến Đạt')."""
    if not s or len(s) % 2 != 0 or not re.fullmatch(r"[0-9a-fA-F]+", s):
        return None
    try:
        return bytes.fromhex(s).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _field(parts: list[str], idx: int) -> str | None:
    """Lấy trường thứ idx, bỏ khoảng trắng/NUL; coi rỗng và '-' (placeholder) là None."""
    if idx >= len(parts):
        return None
    v = parts[idx].strip().strip("\x00").strip()
    return v if v and v != "-" else None


def parse_bhyt_qr(payload: str) -> dict[str, str]:
    """Parse QR thẻ BHYT (VSSID) → {field: value}. Các trường ngăn bằng '|':

      [0] mã số BHYT          [1] họ tên (HEX UTF-8)   [2] ngày sinh dd/MM/yyyy
      [3] giới tính 1=Nam/2=Nữ                          [5] mã đối tượng
      [6] giá trị sử dụng từ  [8] ngày cấp              [12] đủ 5 năm liên tục
      [15] nơi cấp/đổi (HEX UTF-8)

    Chỉ trả trường giải mã chắc chắn; trường rỗng/'-' bị loại. Ngày giữ nguyên dạng
    thô dd/MM/yyyy (pipeline tự chuẩn hoá ISO theo kiểu field).
    """
    if not payload:
        return {}
    parts = payload.split("\x00", 1)[0].split("|")
    out: dict[str, str] = {}

    id_number = _field(parts, 0)
    # Mẫu MỚI: mã số 10 số. Mẫu CŨ: 15 ký tự (2 chữ + 13 số, vd 'HS4010120878837').
    if id_number and re.fullmatch(r"\d{10}|[A-Z]{2}\d{13}", id_number):
        out["idNumber"] = id_number

    name = _field(parts, 1)
    if name:
        out["fullName"] = _hex_to_text(name) or name

    for key, idx in (("dateOfBirth", 2), ("objectCode", 5), ("validFrom", 6),
                     ("dateOfIssue", 8), ("fiveYearContinuous", 12)):
        v = _field(parts, idx)
        if v:
            out[key] = v

    sex = _field(parts, 3)
    if sex in {"1", "2"}:
        out["sex"] = "Nam" if sex == "1" else "Nữ"

    # Mẫu CŨ: [4] = địa chỉ/nơi thường trú (HEX). Mẫu MỚI: [4]='-' (bỏ), nơi cấp ở [15].
    res = _field(parts, 4)
    if res and (dec := _hex_to_text(res)):
        out["placeOfResidence"] = dec

    place = _field(parts, 15)
    if place:
        out["issuePlace"] = _hex_to_text(place) or place

    return out


def _ddmmyyyy(s: str) -> str:
    """QR CCCD ghi ngày dạng ddMMyyyy liền (vd '29031988') → 'dd/MM/yyyy' để pipeline
    (_post → dates.to_iso) chuẩn hoá ISO. Không khớp thì trả nguyên."""
    return f"{s[0:2]}/{s[2:4]}/{s[4:8]}" if re.fullmatch(r"\d{8}", s) else s


def parse_cccd_qr(payload: str) -> dict[str, str]:
    """Parse QR CCCD gắn chip / Căn cước (cùng định dạng 7 trường ngăn '|'):

      [0] số CCCD (12 số)   [1] số CMND 9 số cũ (có thể rỗng)   [2] họ tên (UTF-8 thường)
      [3] ngày sinh ddMMyyyy   [4] giới tính (Nam/Nữ)   [5] nơi thường trú
      [6] ngày cấp ddMMyyyy

    Dùng cho cả chip mặt trước (có số CMND cũ) lẫn Căn cước mặt sau (trường [1] rỗng,
    có thể thừa trường rỗng phía sau). Tên KHÔNG mã hoá hex (khác QR BHYT).
    """
    if not payload:
        return {}
    parts = payload.split("\x00", 1)[0].split("|")
    out: dict[str, str] = {}

    idn = _field(parts, 0)
    if idn and re.fullmatch(r"\d{12}", idn):
        out["idNumber"] = idn

    old = _field(parts, 1)
    if old and re.fullmatch(r"\d{9,12}", old):
        out["oldIdNumber"] = old

    name = _field(parts, 2)
    if name:
        out["fullName"] = name

    dob = _field(parts, 3)
    if dob:
        out["dateOfBirth"] = _ddmmyyyy(dob)

    sex = _field(parts, 4)
    if sex:
        out["sex"] = sex  # 'Nam'/'Nữ' — norm_sex ở _post

    res = _field(parts, 5)
    if res:
        out["placeOfResidence"] = res

    issue = _field(parts, 6)
    if issue:
        out["dateOfIssue"] = _ddmmyyyy(issue)

    return out


# Registry parser QR theo tên (manifest structuredData.parser). Thêm loại = thêm 1 hàm.
QR_PARSERS = {
    "bhyt_qr": parse_bhyt_qr,
    "cccd_qr": parse_cccd_qr,
}
