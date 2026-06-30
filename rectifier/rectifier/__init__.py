"""rectifier — nắn chỉnh ảnh chụp bị nghiêng/méo/xoay về chữ nhật thẳng hàng.

Pipeline thuần OpenCV (offline, không cần model, không cần Internet):
    Image → Segmentation → 4 góc → Perspective warp → Rotate/Deskew → Enhance → Output

Dùng nhanh:
    >>> from PIL import Image
    >>> from rectifier import Rectifier, preset
    >>> r = Rectifier(preset("general"))      # hoặc "id_card", "document", "receipt", "photo"
    >>> result = r.rectify(Image.open("in.jpg"))
    >>> result.image.save("out.jpg")

Hoặc tiện hơn cho một file:
    >>> from rectifier import rectify_image
    >>> rectify_image("in.jpg", "out.jpg", preset="document")
"""
from __future__ import annotations

from rectifier.config import RectifyConfig, available_presets, preset
from rectifier.core import Rectifier, RectifyResult

__all__ = [
    "Rectifier",
    "RectifyConfig",
    "RectifyResult",
    "preset",
    "available_presets",
    "rectify_image",
]

__version__ = "0.1.0"


def rectify_image(src, dst=None, preset: str = "general", **overrides):
    """Nắn một file ảnh và (tùy chọn) lưu ra `dst`. Trả về RectifyResult.

    `src`/`dst` là đường dẫn file. `preset` + `overrides` dựng RectifyConfig.
    """
    from PIL import Image as _Image

    from rectifier.config import preset as _preset

    cfg = _preset(preset, **overrides)
    result = Rectifier(cfg).rectify(_Image.open(src))
    if dst is not None:
        result.image.save(dst)
    return result
