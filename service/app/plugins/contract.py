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
    anchors: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    strategy: str = "label_anchored"   # roi_fixed | label_anchored
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
            anchors=classify.get("anchors", []),
            signals=classify.get("signals", []),
            strategy=extraction.get("strategy", "label_anchored"),
            preprocess=extraction.get("preprocess", d.get("preprocess", [])),
            structured=[StructuredSpec.from_dict(s) for s in d.get("structuredData", [])],
            fields=[FieldSpec.from_dict(f) for f in extraction.get("fields", [])],
            confidence_weights=d.get("confidence", {}).get("fieldWeights", {}),
            cross_checks=d.get("crossChecks", []),
        )
