"""Smoke test khung — chạy đầu-cuối với stub. `pytest` trong thư mục service/."""
import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture(autouse=True)
def _force_stub_backend():
    """Smoke test kiểm API, không cần OCR thật → ép stub cho nhanh & tất định."""
    os.environ["DIP_OCR_BACKEND"] = "stub"
    yield


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 40), (200, 200, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def test_health_and_plugins():
    with TestClient(app) as client:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        r = client.get("/api/v1/doctypes")
        codes = [d["code"] for d in r.json()["docTypes"]]
        assert "cccd_2024_back" in codes


def test_extract_with_hint_returns_schema():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/extract",
            files={"image": ("card.jpg", _jpeg_bytes(), "image/jpeg")},
            data={"docTypeHint": "cccd_2024_back"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["documentType"] == "cccd_2024_back"
        # Chưa cài PaddleOCR → OCR rỗng: trường có mặt (schema nhất quán) + cảnh báo
        assert "placeOfResidence" in body["fields"]
        assert "ocr_no_text" in body["warnings"]


def test_extract_unknown_without_hint():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/extract",
            files={"image": ("card.jpg", _jpeg_bytes(), "image/jpeg")},
        )
        assert r.status_code == 200
        assert r.json()["documentType"] == "unknown"
