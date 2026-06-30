"""Cấu hình pytest: tách test CHẬM (nạp RapidOCR + OCR thật) sau cờ --runslow.

Mặc định `pytest` chỉ chạy test NHANH (không cần model): golden (chống hồi quy shared
code), fixture, unit, smoke — đủ bắt lỗi shared code. Muốn kiểm OCR thật end-to-end:
`pytest --runslow`.
"""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False,
        help="chạy cả test chậm (nạp RapidOCR, OCR thật trên ảnh mẫu)",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: test chậm (nạp model OCR, chạy OCR thật)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="test chậm — thêm --runslow để chạy")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
