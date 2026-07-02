"""Endpoints REST (DOC-07). Upload ảnh bằng multipart/form-data (DEC-040)."""
from __future__ import annotations

import asyncio
import io
import uuid

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app import __version__
from app.models.response import (
    DocTypeInfo,
    ExtractResponse,
    HealthResponse,
    VersionResponse,
)
from app.pipeline.classifier import FAMILIES
from app.settings import settings

router = APIRouter(prefix=settings.api_prefix)

# Nhãn hiển thị tiếng Việt cho mỗi docType (DOC-01).
DOC_TYPE_LABELS = {
    "cccd_chip_front": "CCCD gắn chip - Mặt trước",
    "cmnd_9": "CMND 9 số",
    "cmnd_12": "CMND 12 số",
    "passport_vn": "Hộ chiếu Việt Nam",
    "gplx_pet": "GPLX PET",
    "bhyt": "Thẻ BHYT",
    "the_dang_vien": "Thẻ Đảng viên",
    "the_quan_nhan": "Thẻ quân nhân",
    "cccd_2024_front": "Căn cước 2024 - Mặt trước",
    "cccd_2024_back": "Căn cước 2024 - Mặt sau",
}


def _check_api_key(x_api_key: str | None) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Sai hoặc thiếu API key"})


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    state = request.app.state
    return HealthResponse(
        status="ok",
        modelsWarm=getattr(state, "models_warm", False),
        uptimeSec=int(asyncio.get_event_loop().time() - state.start_time),
        queueDepth=settings.max_concurrency - state.semaphore._value,  # noqa: SLF001
    )


@router.get("/version", response_model=VersionResponse)
async def version(request: Request) -> VersionResponse:
    plugins = {m.doc_type: m.version for m in request.app.state.plugins.all()}
    backend = getattr(request.app.state, "ocr_backend", "unknown")
    return VersionResponse(
        service=__version__,
        engine={"recognize": backend, "detect": "RapidOCR-det"},
        plugins=plugins,
    )


@router.get("/doctypes")
async def doctypes(request: Request) -> dict[str, list[DocTypeInfo]]:
    items = [
        DocTypeInfo(code=m.doc_type, label=m.display_name, ready=m.ready)
        for m in request.app.state.plugins.all()
    ]
    return {"docTypes": items}


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    request: Request,
    image: UploadFile = File(...),
    docTypeHint: str | None = Form(default=None),
    returnImage: str = Form(default="none"),
    # Client (app Android) đã xoay ảnh đúng chiều (áp EXIF trước khi gửi) → bỏ dò hướng,
    # OCR 1 lượt (nhanh ~3-4×). Chỉ đặt true khi CHẮC ảnh thẳng.
    assumeUpright: str = Form(default="false"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> ExtractResponse:
    _check_api_key(x_api_key)
    request_id = str(uuid.uuid4())

    # docTypeHint BẮT BUỘC (DEC-047): cán bộ luôn chọn loại (hoặc họ cmnd/cccd) trên app
    # trước khi chụp → phân loại dựa hint là chính, KHÔNG đoán mù. Hợp lệ = docType đã biết
    # hoặc họ thô cmnd/cccd (hệ thống tự detect loại con).
    hint = (docTypeHint or "").strip()
    allowed = {m.doc_type for m in request.app.state.plugins.all()} | FAMILIES
    if not hint:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_request", "message": "Thiếu docTypeHint (bắt buộc)"},
        )
    if hint not in allowed:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_request",
                    "message": f"docTypeHint không hợp lệ: {hint!r}"},
        )

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "Thiếu ảnh"})
    if len(raw) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail={"code": "image_too_large", "message": "Ảnh vượt giới hạn"})
    try:
        pil = Image.open(io.BytesIO(raw))
        # Áp orientation EXIF (ảnh điện thoại lưu cảm biến NGANG + cờ xoay) rồi mới bỏ EXIF.
        # Không làm bước này → ảnh vào NẰM NGHIÊNG → auto-orient phải OCR 4 hướng (chậm 3-4×).
        pil = ImageOps.exif_transpose(pil).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "Ảnh không hợp lệ"})

    engine = request.app.state.engine
    sem: asyncio.Semaphore = request.app.state.semaphore

    async with sem:  # ADR-010: bounded concurrency
        try:
            resp: ExtractResponse = await asyncio.wait_for(
                asyncio.to_thread(
                    engine.run, request_id, pil, hint,
                    {"returnImage": returnImage,
                     "assumeUpright": str(assumeUpright).strip().lower() in ("1", "true", "yes")}
                ),
                timeout=settings.request_timeout_sec,
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=429, detail={"code": "too_busy", "message": "Quá tải, thử lại"})

    if "anh_qua_kem" in resp.errors:
        raise HTTPException(status_code=422, detail={"code": "image_quality_too_low", "message": "Ảnh quá kém"})

    resp.documentTypeLabel = DOC_TYPE_LABELS.get(resp.documentType, resp.documentTypeLabel)
    return resp
