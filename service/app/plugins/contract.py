"""Plugin contract — mô hình manifest YAML (DOC-05 §4) đã validate."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldSpec:
    name: str
    labels: list[str] = field(default_factory=list)
    take: str = "after_colon"          # DOC-05 §4.4
    source: list[str] = field(default_factory=lambda: ["ocr"])
    type: str = "text_vi"              # DOC-08 §1
    required: bool = False
    validate: dict[str, Any] = field(default_factory=dict)
    normalize: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    cross_check: bool = False
    cross_check_province: bool = False
    multiline: bool = False
    # Ghép giá trị từ các trường khác khi bóc trực tiếp không được (vd hộ chiếu MỚI tách
    # 'Họ/Surname' + 'Chữ đệm và tên/Given names' → fullName = surname + givenNames).
    compose_from: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FieldSpec":
        return cls(
            name=d["name"],
            labels=d.get("labels", []),
            take=d.get("take", "after_colon"),
            source=d.get("source", ["ocr"]),
            type=d.get("type", "text_vi"),
            required=d.get("required", False),
            validate=d.get("validate", {}),
            normalize=d.get("normalize", []),
            checks=d.get("checks", []),
            cross_check=d.get("crossCheck", False),
            cross_check_province=d.get("crossCheckProvince", False),
            multiline=d.get("multiline", False),
            compose_from=d.get("composeFrom", []),
        )


@dataclass
class StructuredSpec:
    kind: str                          # qr | mrz | barcode
    parser: str                        # cccd_qr | mrz_td1 | mrz_td3 | bhyt_qr ...
    maps_to: list[str] = field(default_factory=list)
    format: str | None = None          # vd td1 / td3
    roi: dict[str, int] | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StructuredSpec":
        return cls(
            kind=d["kind"],
            parser=d.get("parser", ""),
            maps_to=d.get("mapsTo", []),
            format=d.get("format"),
            roi=d.get("roi"),
        )


@dataclass
class Manifest:
    doc_type: str
    display_name: str
    version: str = "1.0"
    ready: bool = True
    # Họ giấy tờ cho hint thô từ client (DEC: client chỉ gửi 'cmnd'/'cccd', hệ thống tự
    # detect loại con). None = không thuộc họ nào (gplx, bhyt, the_dang_vien...).
    family: str | None = None
    anchors: list[str] = field(default_factory=list)
    # Anti-anchor: nếu CÓ trong text thì LOẠI loại này (phân biệt look-alike, vd
    # 'CĂN CƯỚC' (mới) phải KHÔNG có 'CÔNG DÂN').
    excludes: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    strategy: str = "label_anchored"   # roi_fixed | label_anchored
    # QR/MRZ đọc được là ĐỦ → lấy toàn bộ từ structured và BỎ QUA OCR (ADR-006). Chỉ bật
    # cho loại mà structured chứa mọi trường cần (vd BHYT: QR đủ; CCCD chip thì KHÔNG vì
    # thiếu quê quán/hạn dùng).
    structured_complete: bool = False
    preprocess: list[str] = field(default_factory=list)
    structured: list[StructuredSpec] = field(default_factory=list)
    fields: list[FieldSpec] = field(default_factory=list)
    confidence_weights: dict[str, float] = field(default_factory=dict)
    cross_checks: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Manifest":
        classify = d.get("classify", {})
        extraction = d.get("extraction", {})
        return cls(
            doc_type=d["docType"],
            display_name=d.get("displayName", d["docType"]),
            version=str(d.get("version", "1.0")),
            ready=d.get("ready", True),
            family=d.get("family"),
            anchors=classify.get("anchors", []),
            excludes=classify.get("excludes", []),
            signals=classify.get("signals", []),
            strategy=extraction.get("strategy", "label_anchored"),
            structured_complete=d.get("structuredComplete", False),
            preprocess=extraction.get("preprocess", d.get("preprocess", [])),
            structured=[StructuredSpec.from_dict(s) for s in d.get("structuredData", [])],
            fields=[FieldSpec.from_dict(f) for f in extraction.get("fields", [])],
            confidence_weights=d.get("confidence", {}).get("fieldWeights", {}),
            cross_checks=d.get("crossChecks", []),
        )
