"""Pydantic models cho response — schema thống nhất (DOC-07, NFR-005)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["structured", "ocr", "derived"]  # derived = suy từ quy tắc (vd sex từ số định danh)


class FieldValue(BaseModel):
    """Một trường dữ liệu đầu ra (DOC-07 §4.2)."""

    value: str | None = None
    confidence: float = 0.0
    source: Source = "ocr"
    raw: str | None = None


class ImagePayload(BaseModel):
    format: str = "jpeg"
    base64: str
    kind: Literal["rectified", "annotated"] = "rectified"


class ExtractResponse(BaseModel):
    """JSON trả về của API-001 /extract (DOC-07 §4.2)."""

    requestId: str
    documentType: str
    documentTypeLabel: str | None = None
    classificationConfidence: float = 0.0
    processingTimeMs: int = 0
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    overallConfidence: float = 0.0
    structuredDataUsed: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)  # ms theo stage (DOC-10)
    image: ImagePayload | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    requestId: str
    error: ErrorBody


class DocTypeInfo(BaseModel):
    code: str
    label: str
    ready: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    modelsWarm: bool = False
    uptimeSec: int = 0
    queueDepth: int = 0


class VersionResponse(BaseModel):
    service: str
    engine: dict[str, str]
    plugins: dict[str, str]
