"""Đọc dữ liệu máy đọc (QR/MRZ/barcode) — structured-data-first (ADR-006)."""
from .qr import QR_PARSERS, decode_qr, parse_bhyt_qr, parse_cccd_qr
from .reader import RealStructuredReader

__all__ = [
    "RealStructuredReader",
    "QR_PARSERS",
    "decode_qr",
    "parse_bhyt_qr",
    "parse_cccd_qr",
]
