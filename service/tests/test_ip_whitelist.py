"""Whitelist IP (DOC-11 §7, DEC-087) — parser CIDR + logic cho phép + middleware 403."""
from app.security import IPWhitelistMiddleware, ip_allowed, parse_networks

DEFAULT = "127.0.0.1/32,192.168.0.0/24"


def test_parse_skips_invalid():
    nets = parse_networks("127.0.0.1/32, khong-hop-le, 192.168.0.0/24")
    assert len(nets) == 2


def test_localhost_and_lan_allowed():
    nets = parse_networks(DEFAULT)
    assert ip_allowed("127.0.0.1", nets)
    assert ip_allowed("192.168.0.50", nets)     # Android cùng LAN
    assert ip_allowed("192.168.0.255", nets)


def test_outside_blocked():
    nets = parse_networks(DEFAULT)
    assert not ip_allowed("192.168.1.10", nets)  # subnet khác
    assert not ip_allowed("10.0.0.5", nets)
    assert not ip_allowed("8.8.8.8", nets)


def test_empty_disables_whitelist():
    assert ip_allowed("8.8.8.8", parse_networks("")) is True


def test_non_ip_host_not_blocked():
    # Starlette TestClient gửi host 'testclient' → không phải IP → KHÔNG chặn (test chạy được).
    assert ip_allowed("testclient", parse_networks(DEFAULT)) is True


def _app():
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(IPWhitelistMiddleware, allowed_ips=DEFAULT)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_middleware_allows_lan_ip():
    from fastapi.testclient import TestClient

    client = TestClient(_app(), client=("192.168.0.77", 5000))  # Android cùng LAN
    assert client.get("/ping").status_code == 200


def test_middleware_blocks_outside_ip():
    from fastapi.testclient import TestClient

    client = TestClient(_app(), client=("10.0.0.9", 5000))      # ngoài dải → 403
    r = client.get("/ping")
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"
