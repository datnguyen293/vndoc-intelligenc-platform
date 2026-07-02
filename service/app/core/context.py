"""ProcessingContext — trạng thái trung gian truyền qua các stage (DOC-03 §6)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.models.response import FieldValue


@dataclass
class ProcessingContext:
    request_id: str
    options: dict[str, Any] = field(default_factory=dict)

    # Ảnh qua các bước (numpy array khi gắn OpenCV; để Any cho skeleton)
    image_original: Any = None
    image_rectified: Any = None

    # Kết quả phân loại
    document_polygon: Any = None
    document_type: str = "unknown"
    classification_confidence: float = 0.0

    # Dữ liệu máy đọc (QR/MRZ/barcode) đã parse -> {field_name: value}
    structured_data: dict[str, str] = field(default_factory=dict)
    structured_used: list[str] = field(default_factory=list)

    # Kết quả OCR theo ROI/dòng (thô)
    ocr_results: dict[str, Any] = field(default_factory=dict)
    # Cho returnImage: dòng OCR (box) + ảnh ĐÃ XOAY mà box thuộc về (annotate cho khớp).
    ocr_lines: list = field(default_factory=list)
    ocr_image: Any = None

    # Trường sau validate/normalize
    fields: dict[str, FieldValue] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Đo thời gian từng stage (DOC-06 §4)
    timings: dict[str, float] = field(default_factory=dict)
    _t0: float = field(default_factory=time.perf_counter)

    def mark(self, stage: str, start: float) -> None:
        self.timings[stage] = (time.perf_counter() - start) * 1000.0

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000.0)
