"""Kiểm soát truy cập theo IP (DOC-11 §7, DEC-087).

Service bind 0.0.0.0 để thiết bị Android CÙNG LAN gọi được (không thể qua 127.0.0.1);
an toàn nhờ whitelist dải CIDR. Client ngoài dải cho phép → 403.

Host không phải địa chỉ IP (vd Starlette `TestClient` gửi host 'testclient') → BỎ QUA
kiểm tra: đó không phải client mạng thật, và giữ cho test không cần mock IP.
"""
from __future__ import annotations

import ipaddress
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger("dip.security")


def parse_networks(raw: str) -> list:
    """'127.0.0.1/32, 192.168.0.0/24' → [IPv4Network, ...]. Dải sai bị bỏ (cảnh báo log).

    KHÔNG giới hạn (cho MỌI IP — dùng cho môi trường TESTING): để rỗng, hoặc đặt
    `DIP_ALLOWED_IPS=*` / `all` / `0.0.0.0/0` → trả [] (whitelist tắt)."""
    raw = (raw or "").strip()
    if raw == "" or raw.lower() in ("*", "all", "0.0.0.0/0", "::/0"):
        return []
    nets: list = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            log.warning("Bỏ qua dải IP không hợp lệ trong DIP_ALLOWED_IPS: %r", part)
    return nets


def ip_allowed(host: str, networks: list) -> bool:
    """True nếu host thuộc một dải cho phép. networks rỗng = tắt whitelist (cho tất cả).
    host không parse được thành IP (vd 'testclient') → True (không chặn client phi-IP)."""
    if not networks:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return any(ip in net for net in networks)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Chặn request có client IP ngoài whitelist trước khi vào route."""

    def __init__(self, app, allowed_ips: str) -> None:
        super().__init__(app)
        self.networks = parse_networks(allowed_ips)
        if not self.networks:
            log.warning(
                "⚠️  Whitelist IP ĐANG TẮT (DIP_ALLOWED_IPS rỗng/'*'/'all') — CHO PHÉP MỌI IP "
                "truy cập. CHỈ dùng cho môi trường testing, KHÔNG dùng thật."
            )

    async def dispatch(self, request: Request, call_next):
        client = request.client
        host = client.host if client else None
        if host is not None and not ip_allowed(host, self.networks):
            log.warning("Chặn truy cập ngoài whitelist: %s", host)
            return JSONResponse(
                status_code=403,
                content={"code": "forbidden", "message": "IP không được phép truy cập"},
            )
        return await call_next(request)
