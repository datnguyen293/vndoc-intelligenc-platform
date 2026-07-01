"""FastAPI app — khởi tạo warm plugin + pipeline (DOC-03, DOC-10).

Chạy: uvicorn app.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import router
from app.cv import build_preprocessors
from app.extract import LabelAnchoredExtractor
from app.ocr import (
    StubQualityChecker,
    create_ocr_engine,
)
from app.pipeline import PipelineEngine
from app.pipeline.classifier import RuleClassifier
from app.plugins import PluginManager
from app.security import IPWhitelistMiddleware
from app.settings import settings
from app.structured import RealStructuredReader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dip")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nạp plugin warm một lần (DEC-022)
    plugins = PluginManager(settings.plugins_dir)
    plugins.load_all()
    log.info("Đã nạp %d plugin từ %s", plugins.count, settings.plugins_dir)

    ocr = create_ocr_engine()  # VietOCR/RapidOCR nếu cài được, ngược lại stub
    detector, rectifier = build_preprocessors(settings.card_detect)
    engine = PipelineEngine(
        plugins=plugins,
        quality=StubQualityChecker(),
        detector=detector,
        rectifier=rectifier,
        classifier=RuleClassifier(plugins),
        structured=RealStructuredReader(plugins),
        ocr=ocr,
        extractor=LabelAnchoredExtractor(),
    )

    app.state.plugins = plugins
    app.state.engine = engine
    app.state.semaphore = asyncio.Semaphore(settings.max_concurrency)
    app.state.start_time = asyncio.get_event_loop().time()
    app.state.ocr_backend = getattr(ocr, "backend_name", ocr.__class__.__name__)
    app.state.models_warm = app.state.ocr_backend != "StubOcrEngine"
    log.info("OCR backend recognition: %s", app.state.ocr_backend)
    yield


app = FastAPI(title="DIP OCR Service", version=__version__, lifespan=lifespan)
# Whitelist IP (DEC-087): chặn client ngoài dải cho phép (mặc định 127.0.0.1 + 192.168.0.0/24).
app.add_middleware(IPWhitelistMiddleware, allowed_ips=settings.allowed_ips)
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "DIP OCR Service", "version": __version__, "docs": "/docs"}
