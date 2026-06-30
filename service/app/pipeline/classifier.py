"""RuleClassifier — phân loại thuần luật từ text OCR (ADR-008, ADR-012).

Không model/train: chấm điểm mỗi loại theo số cụm chữ neo (`classify.anchors` trong
manifest) xuất hiện trong text OCR (so khớp bỏ dấu + bỏ space → bền OCR yếu).
"""
from __future__ import annotations

from typing import Any

from app.extract.textutil import key
from app.plugins.manager import PluginManager


class RuleClassifier:
    def __init__(self, plugins: PluginManager) -> None:
        self.plugins = plugins
        self.known = {m.doc_type for m in plugins.all()}

    def classify(self, lines: list[Any], hint: str | None = None) -> tuple[str, float]:
        # Hint hợp lệ → tin tưởng (client đã chọn loại). Vẫn cho phép phân loại nếu không.
        if hint and hint in self.known:
            return hint, 0.95

        joined = key(" ".join(getattr(l, "text", "") for l in lines))
        best, best_score = None, 0
        for m in self.plugins.all():
            score = sum(1 for a in m.anchors if key(a) and key(a) in joined)
            if score > best_score:
                best, best_score = m.doc_type, score

        if best and best_score > 0:
            return best, min(0.99, 0.6 + 0.2 * best_score)
        return "unknown", 0.0
