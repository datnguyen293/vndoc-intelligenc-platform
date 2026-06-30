"""Protocol cho từng thành phần thay-thế-được (DOC-03 §8, ADR-003/004).

Mỗi Protocol là một ranh giới: bản stub (app/ocr/stub.py) hiện thực để chạy khung;
sau này thay bằng PaddleOCR/VietOCR/OpenVINO mà không sửa pipeline.
"""
from __future__ import annotations

from typing import Any, Protocol


class ImageQualityChecker(Protocol):
    def check(self, image: Any) -> tuple[bool, dict[str, float]]:
        """Trả (đạt?, chỉ số). Đạt=False → reject sớm (FR-002)."""
        ...


class DocumentDetector(Protocol):
    def detect(self, image: Any) -> Any:
        """Tìm khung giấy tờ → polygon 4 góc (FR-003)."""
        ...


class Rectifier(Protocol):
    def rectify(self, image: Any, polygon: Any) -> Any:
        """Nắn phối cảnh + chuẩn hóa hướng 0/90/180/270 (FR-004, DEC-009)."""
        ...


class Classifier(Protocol):
    def classify(self, lines: list[Any], hint: str | None = None) -> tuple[str, float]:
        """Phân loại thuần luật từ text OCR (ADR-008) → (doc_type, confidence)."""
        ...


class StructuredReader(Protocol):
    def read(self, image: Any, doc_type: str) -> tuple[dict[str, str], list[str]]:
        """Đọc QR/MRZ/barcode (ADR-006) → ({field: value}, [kind_used])."""
        ...


class OcrEngine(Protocol):
    def recognize(self, image: Any) -> list[Any]:
        """OCR thô → danh sách OcrLine (text + vị trí + confidence) (FR-008/009).

        Tách det+rec thành một bước trả 'dòng có toạ độ'; việc gán trường (label-
        anchored / roi) do FieldExtractor đảm nhiệm (DOC-06 S7→S8).
        """
        ...
