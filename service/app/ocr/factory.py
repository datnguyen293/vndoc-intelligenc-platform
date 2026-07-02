"""Chọn OCR engine theo thứ tự ưu tiên; fallback stub để service không chết.

Thứ tự: PaddleOCR (ADR-004 nguyên bản) → RapidOCR (PP-OCR trên ONNX, dễ cài) → Stub.
Đặt biến môi trường DIP_OCR_BACKEND=paddle|rapid|stub để ép chọn.
"""
from __future__ import annotations

import logging
import os

from app.ocr.orient import OrientingOcr
from app.ocr.stub import StubOcrEngine
from app.settings import settings

log = logging.getLogger("dip.ocr")


def _try_paddle():
    from app.ocr.paddle_engine import PaddleOcrEngine
    return PaddleOcrEngine()


def _try_rapid():
    from app.ocr.rapidocr_engine import RapidOcrEngine
    return RapidOcrEngine()


def _try_vietocr():
    from app.ocr.vietocr_engine import VietOcrEngine
    return VietOcrEngine()


def _build_orient_classifier():
    """Tạo OrientationClassifier nếu bật cờ + có model ONNX; lỗi/thiếu → None (dùng OCR-search)."""
    if not settings.orient_classifier or not settings.orient_model.exists():
        return None
    try:
        from app.cv.orient_model import OrientationClassifier
        clf = OrientationClassifier(settings.orient_model)
        log.info("Orientation classifier BẬT (model %s, ngưỡng %.2f)",
                 settings.orient_model.name, settings.orient_min_conf)
        return clf
    except Exception as exc:  # noqa: BLE001
        log.warning("Không bật được orientation classifier (%s) → dùng OCR-search", exc)
        return None


def create_ocr_engine():
    forced = os.environ.get("DIP_OCR_BACKEND", "").lower()
    # Mặc định: ưu tiên VietOCR (đúng dấu tiếng Việt) → RapidOCR (nhanh) → stub.
    order = {
        "paddle": [_try_paddle],
        "vietocr": [_try_vietocr],
        "rapid": [_try_rapid],
        "stub": [],
    }.get(forced, [_try_vietocr, _try_rapid])

    clf = _build_orient_classifier()
    for builder in order:
        try:
            engine = builder()
            # Bọc nắn hướng cho engine thật (stub không cần)
            return OrientingOcr(engine, enabled=settings.auto_orient,
                                classifier=clf, min_conf=settings.orient_min_conf)
        except Exception as exc:  # noqa: BLE001
            log.warning("OCR backend %s không dùng được: %s", builder.__name__, exc)

    log.warning(
        "Không có OCR backend nào → StubOcrEngine (kết quả rỗng). "
        "Cài: pip install rapidocr-onnxruntime  (hoặc paddleocr paddlepaddle)"
    )
    return StubOcrEngine()
