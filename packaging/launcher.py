"""launcher — entrypoint production của VNDoc OCR Service (DOC-11 §5).

Khác chế độ dev (`uvicorn app.main:app`): launcher tự trỏ config/models/plugins theo
THƯ MỤC CÀI ĐẶT (không phụ thuộc thư mục hiện hành), rồi chạy uvicorn nghe 127.0.0.1:11001
theo `config\\vndoc.env`. Đây là tiến trình mà NSSM (Windows Service) gọi:

    <install>\\runtime\\python.exe  <install>\\launcher.py

File này sẽ được PyArmor bảo vệ khi đóng gói (DOC-11 §8) — giữ đơn giản, không bí mật gì.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Thư mục cài đặt = nơi chứa launcher (cạnh app/, rectifier/, models/, plugins/, config/).
INSTALL_ROOT = Path(__file__).resolve().parent


def _bootstrap_env() -> None:
    """Chuẩn bị sys.path + biến môi trường TRƯỚC khi import app (settings đọc lúc import)."""
    root = str(INSTALL_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)  # cho import app/ và rectifier/ nằm cạnh launcher

    # Trỏ file config để settings.py nạp (DOC-11 §7). setdefault → không đè nếu đã set sẵn.
    os.environ.setdefault("VNDOC_CONFIG", str(INSTALL_ROOT / "config" / "vndoc.env"))
    # models/ & plugins/ cạnh thư mục cài (settings tự suy từ SERVICE_ROOT, nhưng đặt tường
    # minh cho chắc khi bố cục cài đặt khác cây nguồn).
    os.environ.setdefault("DIP_MODELS_DIR", str(INSTALL_ROOT / "models"))
    os.environ.setdefault("DIP_PLUGINS_DIR", str(INSTALL_ROOT / "plugins"))


def main() -> int:
    _bootstrap_env()

    # (DOC-11 §9) ĐIỂM MÓC kiểm tra license theo máy — CHƯA bật ở V1, chuẩn bị sẵn:
    #   from launcher_license import verify_or_exit
    #   verify_or_exit(INSTALL_ROOT)   # thiếu/không hợp lệ → thoát mã lỗi rõ ràng

    import uvicorn

    from app.settings import settings  # import SAU _bootstrap_env để settings đọc đúng config

    # DEC-070: 1 process, model warm chia sẻ mọi request (KHÔNG nhiều worker → tránh nạp
    # model nhiều lần & vỡ ngân sách RAM NFR-008).
    uvicorn.run(
        "app.main:app",
        host=settings.host,      # mặc định 127.0.0.1 (nội bộ máy, NFR-007)
        port=settings.port,      # mặc định 11001 (DEC-083)
        workers=1,
        log_config=None,         # dùng logging cấu hình trong app.main
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
