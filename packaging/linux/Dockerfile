# VNDoc OCR service — bản Linux/Docker (DOC-11, bổ sung 2026-07-02).
# Build từ THƯ MỤC GỐC repo (context = .), KHÔNG phải packaging/linux:
#   docker build -f packaging/linux/Dockerfile -t vndoc-ocr:0.1.0 .
# Ảnh tự chứa (bundle model). CPU-only (ADR-002).
FROM python:3.11-slim

# libglib2.0-0 + libgl1: OpenCV (dù headless vẫn cần libglib; libgl1 cho vài op).
# libgomp1: OpenMP cho torch/onnxruntime. curl: HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Deps trước (tận dụng cache lớp khi chỉ đổi source).
COPY packaging/linux/requirements-linux.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 2) Source CỦA TA + model offline (KHÔNG copy samples/tests/venv — xem .dockerignore).
#    Cấu trúc gương service/ để settings.py (SERVICE_ROOT=/app) tự trỏ plugins/ + models/.
COPY service/app        /app/app
COPY service/plugins    /app/plugins
COPY rectifier/rectifier /app/rectifier
COPY service/models     /app/models
COPY packaging/linux/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DIP_HOST=0.0.0.0 \
    DIP_PORT=11001 \
    DIP_RECTIFY_CORNER_FALLBACK=true \
    DIP_ORIENT_CLASSIFIER=true \
    DIP_OCR_DEVICE=cpu

EXPOSE 11001
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD curl -fsS http://127.0.0.1:11001/api/v1/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
