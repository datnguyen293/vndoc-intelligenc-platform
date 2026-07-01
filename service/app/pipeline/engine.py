"""PipelineEngine — điều phối các stage (DOC-03 §4, DOC-06).

Luồng: quality → detect → rectify → classify → structured-read → OCR thô →
trích xuất trường (label-anchored) → response. Mọi thành phần tiêm qua constructor
nên thay model thật không đụng pipeline.
"""
from __future__ import annotations

import time
from typing import Any

from app.core.context import ProcessingContext
from app.core.interfaces import (
    Classifier,
    DocumentDetector,
    ImageQualityChecker,
    OcrEngine,
    Rectifier,
    StructuredReader,
)
from app.extract.anchored import LabelAnchoredExtractor
from app.models.response import ExtractResponse
from app.plugins.manager import PluginManager


class PipelineEngine:
    def __init__(
        self,
        plugins: PluginManager,
        quality: ImageQualityChecker,
        detector: DocumentDetector,
        rectifier: Rectifier,
        classifier: Classifier,
        structured: StructuredReader,
        ocr: OcrEngine,
        extractor: LabelAnchoredExtractor,
    ) -> None:
        self.plugins = plugins
        self.quality = quality
        self.detector = detector
        self.rectifier = rectifier
        self.classifier = classifier
        self.structured = structured
        self.ocr = ocr
        self.extractor = extractor

    def run(
        self,
        request_id: str,
        image: Any,
        doc_type_hint: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ExtractResponse:
        ctx = ProcessingContext(request_id=request_id, options=options or {})
        ctx.image_original = image

        # S1 — Quality check (FR-002)
        t = time.perf_counter()
        ok, _metrics = self.quality.check(image)
        ctx.mark("quality", t)
        if not ok:
            ctx.errors.append("anh_qua_kem")
            return self._build(ctx)

        # S2 — Detection khung thẻ (FR-003)
        t = time.perf_counter()
        ctx.document_polygon = self.detector.detect(image)
        ctx.mark("detect", t)

        # S3 — Rectification: warp + resize (FR-004)
        t = time.perf_counter()
        ctx.image_rectified = self.rectifier.rectify(image, ctx.document_polygon)
        ctx.mark("rectify", t)

        # S3.5 — QR-FIRST (ADR-006): thử QR TRƯỚC OCR. Đọc được + plugin
        # `structuredComplete` → lấy TOÀN BỘ trường từ QR và BỎ QUA OCR (nhanh + chính
        # xác). QR hỏng/không khớp → identify=None → rơi xuống đường OCR bên dưới.
        t = time.perf_counter()
        # QR trên ảnh đã rectify + ẢNH GỐC (dự phòng): rectifier có thể crop mất/thu nhỏ QR.
        ident = self.structured.identify(
            ctx.image_rectified, hint=doc_type_hint, image_alt=ctx.image_original
        )
        ctx.mark("structured", t)
        if ident is not None:
            doc_type, structured_fields, used = ident
            manifest = self.plugins.get(doc_type)
            if manifest is not None and manifest.structured_complete:
                ctx.document_type = doc_type
                ctx.classification_confidence = 0.99
                ctx.structured_data = structured_fields
                ctx.structured_used = used
                # Trích xuất CHỈ từ structured (lines rỗng): trường nào QR không có sẽ null.
                fields, warns = self.extractor.extract([], manifest, structured_fields)
                ctx.fields = fields
                ctx.warnings += warns
                return self._build(
                    ctx, label=manifest.display_name, weights=manifest.confidence_weights
                )

        # S4 — OCR thô MỘT LẦN (dùng cho cả phân loại lẫn trích xuất) (FR-008/009)
        t = time.perf_counter()
        lines = self.ocr.recognize(ctx.image_rectified)
        ctx.mark("ocr", t)

        # S5 — Classification thuần luật từ chính text OCR (ADR-008)
        t = time.perf_counter()
        ctx.document_type, ctx.classification_confidence = self.classifier.classify(
            lines, hint=doc_type_hint
        )
        ctx.mark("classify", t)

        manifest = self.plugins.get(ctx.document_type)
        if ctx.document_type == "unknown" or manifest is None:
            ctx.document_type = "unknown"
            ctx.warnings.append("khong_nhan_dang_duoc_loai")
            return self._build(ctx)
        if not manifest.ready:
            ctx.warnings.append("plugin_chua_co_mau")

        # S6 — Structured-data (ADR-006): QR (ảnh) + MRZ (dòng OCR) bù cho OCR
        t = time.perf_counter()
        ctx.structured_data, ctx.structured_used = self.structured.read(
            ctx.image_rectified, ctx.document_type, lines, image_alt=ctx.image_original
        )
        ctx.mark("structured", t)
        if not lines and not ctx.structured_data:
            ctx.warnings.append("ocr_no_text")

        # S7/S8 — Trích xuất trường + chuẩn hóa + validate (DOC-08)
        t = time.perf_counter()
        fields, warns = self.extractor.extract(lines, manifest, ctx.structured_data)
        ctx.fields = fields
        ctx.warnings += warns
        ctx.mark("extract", t)

        return self._build(ctx, label=manifest.display_name, weights=manifest.confidence_weights)

    def _build(self, ctx, label=None, weights=None) -> ExtractResponse:
        weights = weights or {}
        overall = self._overall(ctx.fields, weights)
        return ExtractResponse(
            requestId=ctx.request_id,
            documentType=ctx.document_type,
            documentTypeLabel=label,
            classificationConfidence=round(ctx.classification_confidence, 4),
            processingTimeMs=ctx.elapsed_ms,
            fields=ctx.fields,
            overallConfidence=overall,
            structuredDataUsed=ctx.structured_used,
            warnings=ctx.warnings,
            errors=ctx.errors,
            timings={k: round(v, 1) for k, v in ctx.timings.items()},
        )

    @staticmethod
    def _overall(fields, weights) -> float:
        if not fields:
            return 0.0
        default_w = weights.get("default", 0.1)
        num = den = 0.0
        for name, fv in fields.items():
            w = weights.get(name, default_w)
            num += w * fv.confidence
            den += w
        return round(num / den, 4) if den else 0.0
