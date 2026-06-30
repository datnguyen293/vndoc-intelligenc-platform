"""Cấu hình service — đọc từ biến môi trường, có mặc định hợp lý (DOC-10)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DIP_", env_file=".env", extra="ignore")

    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8080

    # Thư mục plugin (manifest YAML) và model — tách ngoài mã nguồn (FR-018)
    plugins_dir: Path = SERVICE_ROOT / "plugins"
    models_dir: Path = SERVICE_ROOT / "models"

    # Giới hạn & hiệu năng (NFR-001, FR-019)
    max_image_bytes: int = 8 * 1024 * 1024
    max_concurrency: int = 8          # ADR-010: bounded theo số P-core
    request_timeout_sec: float = 3.0

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

    # Bảo mật (NFR-007)
    api_key: str | None = None        # nếu đặt → bắt buộc header X-API-Key
    save_images: bool = False         # mặc định KHÔNG lưu ảnh ra đĩa


settings = Settings()
