"""Tiền xử lý ảnh — dùng package `rectifier` (nắn méo + cắt nền + enhance, offline).

Pipeline (rectifier, preset `id_card`): Segmentation → 4 góc → Corner refine →
Perspective → Auto-rotate → Deskew → Padding → CLAHE → Sharpen. Có "nắn-khi-cần"
(ảnh đã phẳng + lấp khung thì passthrough).
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("dip.cv")


class _NoopDetector:
    """Detector rỗng — rectifier tự segment bên trong, không cần detect riêng."""

    def detect(self, image: Any):
        return None


class _RectifierAdapter:
    """Bọc rectifier.Rectifier vào interface rectifier của pipeline (bỏ qua polygon)."""

    def __init__(self, rectifier) -> None:
        self._r = rectifier

    def rectify(self, image: Any, _polygon: Any):
        return self._r.rectify(image).image


def build_preprocessors(card_detect: bool = True):
    """Trả (detector, rectifier).

    - Có package `rectifier`: dùng preset `id_card`. `card_detect=False` → enabled=False
      (chỉ resize-cap). Thiếu package → stub passthrough.
    """
    from app.ocr.stub import StubDetector, StubRectifier

    try:
        import rectifier
    except Exception as exc:  # noqa: BLE001
        log.warning("Không có package 'rectifier' (%s) → passthrough (stub). "
                    "Cài: pip install -e ../rectifier", exc)
        return StubDetector(), StubRectifier()

    from app.settings import settings

    cfg = rectifier.preset(
        "id_card",
        enabled=card_detect,
        segmenter=settings.rectify_segmenter,
        yolo_weights=settings.yolo_seg_weights,
        clahe=settings.rectify_clahe,
        sharpen=settings.rectify_sharpen,
        denoise=settings.rectify_denoise,
    )
    adapter = _RectifierAdapter(rectifier.Rectifier(cfg))

    # Corner-detector fallback (thử nghiệm) — bọc thêm khi bật + có model ONNX.
    if settings.rectify_corner_fallback and settings.corner_model.exists():
        try:
            from app.cv.corner import CornerAssistRectifier, CornerModel
            model = CornerModel(settings.corner_model)
            adapter = CornerAssistRectifier(adapter, model, settings.corner_min_ratio)
            log.info("Corner-detector fallback BẬT (model %s, ngưỡng %.2f)",
                     settings.corner_model.name, settings.corner_min_ratio)
        except Exception as exc:  # noqa: BLE001
            log.warning("Không bật được corner fallback (%s) → chỉ classic", exc)

    return _NoopDetector(), adapter


__all__ = ["build_preprocessors"]
