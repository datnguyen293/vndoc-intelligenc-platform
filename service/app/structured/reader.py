"""RealStructuredReader — đọc QR/MRZ/barcode theo manifest (ADR-006).

Giữ tham chiếu PluginManager để tra `structuredData` của docType, nên KHÔNG đổi chữ ký
Protocol `read(image, doc_type)` (core/interfaces.py). Mỗi spec: giải mã theo `kind` →
chạy parser → lọc theo `mapsTo` → {field: value}. Lib QR thiếu / ảnh None / không có
mã → ({}, []) (degrade an toàn, pipeline rơi về OCR).
"""
from __future__ import annotations

import re
from typing import Any

from app.plugins.contract import Manifest, StructuredSpec
from app.plugins.manager import PluginManager
from app.structured.mrz import (
    find_mrz_td1,
    find_mrz_td3,
    mrz_td1_checksums_ok,
    mrz_td3_checksums_ok,
    parse_mrz_td1,
    parse_mrz_td3,
)
from app.structured.qr import QR_PARSERS, decode_qr


class RealStructuredReader:
    def __init__(self, plugins: PluginManager) -> None:
        self.plugins = plugins

    def identify(
        self, image: Any, hint: str | None = None
    ) -> tuple[str, dict[str, str], list[str]] | None:
        """QR-first (ADR-006): giải mã QR TRƯỚC OCR; nếu khớp một loại có
        `structuredComplete` → (doc_type, {field: value}, [kind]) để bỏ qua OCR.

        Tự nhận loại từ chính QR: thử parser của từng manifest, ràng buộc bằng regex
        `idNumber` để không nhận nhầm (vd QR CCCD ≠ BHYT). Hint (nếu có) được ưu tiên.
        """
        payloads = decode_qr(image)
        if not payloads:
            return None

        order: list[Manifest] = []
        hinted = self.plugins.get(hint) if hint else None
        if hinted is not None:
            order.append(hinted)
        order += [m for m in self.plugins.all() if m is not hinted]

        for manifest in order:
            if not manifest.structured_complete:
                continue
            for spec in manifest.structured:
                if spec.kind != "qr":
                    continue
                parser = QR_PARSERS.get(spec.parser)
                if parser is None:
                    continue
                for payload in payloads:
                    parsed = parser(payload)
                    if not self._matches(parsed, manifest):
                        continue
                    mapped = {
                        f: parsed[f]
                        for f in (spec.maps_to or parsed.keys())
                        if parsed.get(f)
                    }
                    if mapped:
                        return manifest.doc_type, mapped, [spec.kind]
        return None

    @staticmethod
    def _matches(parsed: dict[str, str], manifest: Manifest) -> bool:
        """QR có đúng loại không: nếu manifest có field idNumber + regex thì idNumber
        giải ra phải khớp; nếu không có regex thì chỉ cần parse ra dữ liệu."""
        if not parsed:
            return False
        for spec in manifest.fields:
            if spec.name == "idNumber":
                rgx = spec.validate.get("regex")
                val = parsed.get("idNumber")
                if rgx and val:
                    return re.fullmatch(rgx, val) is not None
                return bool(val)
        return True

    def read(
        self, image: Any, doc_type: str, lines: list[Any] | None = None
    ) -> tuple[dict[str, str], list[str]]:
        manifest = self.plugins.get(doc_type)
        if manifest is None or not manifest.structured:
            return {}, []

        texts = [getattr(l, "text", "") for l in (lines or [])]
        fields: dict[str, str] = {}
        used: list[str] = []
        for spec in manifest.structured:
            parsed = self._read_one(image, spec, texts)
            if not parsed:
                continue
            # Lọc theo mapsTo (rỗng = nhận tất cả parser trả về); KHÔNG ghi đè trường
            # đã có từ spec trước (thứ tự manifest = thứ tự ưu tiên nguồn structured).
            mapped = {
                f: parsed[f]
                for f in (spec.maps_to or parsed.keys())
                if parsed.get(f) and f not in fields
            }
            if mapped:
                fields.update(mapped)
                if spec.kind not in used:
                    used.append(spec.kind)
        return fields, used

    def _read_one(
        self, image: Any, spec: StructuredSpec, texts: list[str]
    ) -> dict[str, str]:
        if spec.kind == "qr":
            parser = QR_PARSERS.get(spec.parser)
            if parser is None:
                return {}
            for payload in decode_qr(image):
                parsed = parser(payload)
                if parsed:
                    return parsed
            return {}
        if spec.kind == "mrz":
            # CHỈ tin MRZ khi checksum đúng — OCR thường phá ký tự '<' của MRZ thành chữ.
            if spec.format == "td3" or spec.parser == "mrz_td3":
                td = find_mrz_td3(texts)   # hộ chiếu (2 dòng × 44)
                if td and mrz_td3_checksums_ok(td):
                    return parse_mrz_td3(td)
                return {}
            td = find_mrz_td1(texts)       # mặc định td1 (căn cước 2024 mặt sau)
            if td and mrz_td1_checksums_ok(td):
                return parse_mrz_td1(td)
            return {}
        return {}
