"""Cấu hình nắn ảnh + bộ preset cho các loại tài liệu phổ biến.

`RectifyConfig` điều khiển từng stage của pipeline. Mặc định là cấu hình TỔNG QUÁT:
không ép tỉ lệ khung, hợp cho mọi ảnh giấy tờ/tài liệu chụp nghiêng. Dùng `preset()`
để lấy cấu hình tinh chỉnh sẵn (thẻ ID, A4, hóa đơn, ảnh vuông…).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass


@dataclass
class RectifyConfig:
    enabled: bool = True
    segmenter: str = "classic"            # classic | yolo
    yolo_weights: str | None = None
    grabcut_fallback: bool = True         # classic: fallback GrabCut khi nền tương phản thấp

    work: int = 1000                      # độ phân giải để segment (nhanh)
    min_area_ratio: float = 0.10          # vùng tài liệu tối thiểu so với ảnh (chụp xa → để thấp)

    # Validate tỉ lệ khung sau khi tìm tứ giác. None = không ràng buộc (tổng quát).
    ar_min: float | None = None
    ar_max: float | None = None

    # "Nắn-khi-cần": ảnh đã phẳng (lấp khung ≥ skip_fill) + thẳng (skew ≤ skip_skew)
    # → bỏ qua warp để khỏi xê dịch ảnh vốn đã tốt.
    skip_fill: float = 0.90
    skip_skew: float = 3.0

    corner_refine: bool = True
    margin: float = 0.012                 # nới quad ra ngoài (tránh cắt cụt mép)
    rotate_landscape: bool = False        # ép ngang sau warp
    deskew: bool = True                   # sửa nghiêng nhỏ còn lại
    pad_ratio: float = 0.02               # adaptive padding sau warp

    clahe: bool = True
    sharpen: bool = True
    denoise: bool = False                 # chậm hơn → mặc định off

    out_long: int = 2000                  # giới hạn cạnh dài của output


# --- Presets: bản sao RectifyConfig đã tinh chỉnh cho từng loại ---------------
# Mỗi entry là dict các field ghi đè lên mặc định tổng quát.
_PRESETS: dict[str, dict] = {
    # Tổng quát — không ràng buộc tỉ lệ, hợp mọi ảnh tài liệu.
    "general": {},

    # Thẻ ID-1 (CCCD/CMND/GPLX/BHYT, ~85.6×54mm, tỉ lệ ~1.585).
    "id_card": {
        "ar_min": 1.2, "ar_max": 2.3,
        "rotate_landscape": True,
        "skip_fill": 0.88, "skip_skew": 4.0,
    },

    # Trang giấy A4/Letter dọc (tỉ lệ ~1.41/1.29).
    "document": {
        "ar_min": 1.2, "ar_max": 1.6,
        "out_long": 2500,
        "clahe": True, "sharpen": True,
    },

    # Hóa đơn/bill: dài hẹp, không ép tỉ lệ, không xoay ngang.
    "receipt": {
        "ar_min": None, "ar_max": None,
        "rotate_landscape": False,
        "min_area_ratio": 0.10,
        "out_long": 2200,
    },

    # Ảnh/hình vuông: giữ nguyên màu, không tăng tương phản/sắc nét mạnh.
    "photo": {
        "ar_min": None, "ar_max": None,
        "clahe": False, "sharpen": False,
        "deskew": False, "pad_ratio": 0.0,
    },
}


def available_presets() -> list[str]:
    """Danh sách tên preset hợp lệ."""
    return list(_PRESETS)


def preset(name: str = "general", **overrides) -> RectifyConfig:
    """Lấy RectifyConfig theo preset, cho phép ghi đè thêm field.

    Ví dụ: ``preset("id_card", denoise=True, out_long=2400)``.
    """
    if name not in _PRESETS:
        raise ValueError(
            f"Preset không tồn tại: {name!r}. Có: {', '.join(_PRESETS)}"
        )
    cfg = RectifyConfig(**copy.deepcopy(_PRESETS[name]))
    for key, val in overrides.items():
        if not hasattr(cfg, key):
            raise ValueError(f"RectifyConfig không có field: {key!r}")
        setattr(cfg, key, val)
    return cfg
