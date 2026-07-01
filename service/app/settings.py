"""Cấu hình service — đọc từ biến môi trường, có mặc định hợp lý (DOC-10)."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parent.parent

# File cấu hình: bản đóng gói (DOC-11) trỏ `VNDOC_CONFIG` tới `config\vndoc.env` cạnh thư
# mục cài đặt (không phụ thuộc CWD); không đặt thì giữ hành vi dev cũ (`service/.env`).
# Vẫn ưu tiên biến môi trường thật của tiến trình (pydantic-settings đọc env trước env_file).
_CONFIG_FILE = os.environ.get("VNDOC_CONFIG", str(SERVICE_ROOT / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIP_", env_file=_CONFIG_FILE, extra="ignore"
    )

    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8080

    # Thư mục plugin (manifest YAML) và model — tách ngoài mã nguồn (FR-018)
    plugins_dir: Path = SERVICE_ROOT / "plugins"
    models_dir: Path = SERVICE_ROOT / "models"

    # Giới hạn & hiệu năng (NFR-001, FR-019)
    max_image_bytes: int = 8 * 1024 * 1024
    max_concurrency: int = 8          # ADR-010: bounded theo số P-core
    # OCR recognition CPU ~2-4s/ảnh (ảnh xoay recognize×4 tới ~5s) → timeout 3s cũ gây 429
    # oan. Nâng 15s (đổi qua DIP_REQUEST_TIMEOUT_SEC). Model nạp 1 lần lúc startup, KHÔNG
    # tính vào request.
    request_timeout_sec: float = 15.0

    # OCR / tiền xử lý ảnh
    auto_orient: bool = True          # tự nắn hướng 0/90/180/270 (DEC-009)
    # Hiệu năng OCR (NFR-001): giảm cạnh dài ảnh TRƯỚC text-detection (detection tỉ lệ
    # với số pixel; 1280px gần như không mất box so với 2000px nhưng nhanh ~3×). Recognition
    # vẫn crop từ ảnh GỐC để giữ độ nét. ocr_threads: số luồng torch cho recognize (CPU).
    ocr_det_max_side: int = 1280
    ocr_threads: int = 8
    # Thiết bị chạy recognition VietOCR: "auto" | "cpu" | "cuda".
    # auto: tự dùng CUDA nếu có GPU NVIDIA, ngược lại CPU → cùng 1 build chạy được cả máy
    # CÓ và KHÔNG GPU (máy đích Intel i7-14700: GPU tuỳ chọn). Ép tay qua DIP_OCR_DEVICE.
    ocr_device: str = "auto"
    # Document rectification: nắn méo phối cảnh + cắt nền (FR-003/004). Mặc định BẬT vì
    # "nắn-khi-cần": ảnh đã phẳng + lấp khung thì passthrough (không xê dịch OCR), chỉ
    # warp ảnh chụp nghiêng/nhiều nền. Tắt nếu muốn.
    card_detect: bool = True
    rectify_segmenter: str = "classic"     # classic | yolo
    yolo_seg_weights: str | None = None    # đường dẫn weights YOLOv11-seg (nếu dùng yolo)
    rectify_clahe: bool = True
    rectify_sharpen: bool = True
    rectify_denoise: bool = False
    # Corner-detector FALLBACK (thử nghiệm): bật + có model ONNX → khi thẻ NHỎ trên nền,
    # classic hay hỏng thì dùng model detect 4 góc để nắn. Mặc định TẮT (không đổi hành vi).
    rectify_corner_fallback: bool = False
    corner_model: Path = SERVICE_ROOT / "models" / "corner.onnx"
    corner_min_ratio: float = 0.55        # thẻ chiếm < tỉ lệ này của khung → dùng corner

    # Bảo mật (NFR-007)
    api_key: str | None = None        # nếu đặt → bắt buộc header X-API-Key
    save_images: bool = False         # mặc định KHÔNG lưu ảnh ra đĩa
    # Whitelist IP (CIDR, ngăn bằng dấu phẩy) được phép gọi service (DOC-11 §7, DEC-087).
    # Bind 0.0.0.0 để thiết bị Android CÙNG LAN gọi được (không thể qua 127.0.0.1); whitelist
    # giữ an toàn — client ngoài dải → 403. Rỗng = TẮT (cho tất cả). Đổi qua DIP_ALLOWED_IPS.
    allowed_ips: str = "127.0.0.1/32,192.168.0.0/24"


settings = Settings()
