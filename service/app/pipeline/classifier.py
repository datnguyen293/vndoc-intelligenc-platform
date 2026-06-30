"""RuleClassifier — phân loại thuần luật từ text OCR (ADR-008, ADR-012).

Không model/train. Hai chế độ:
- Hint THÔ theo HỌ ('cmnd' | 'cccd'): client không phân biệt loại con, hệ thống tự
  detect trong họ (CMND theo độ dài số; CCCD theo anchor mặt trước/sau).
- Không hint / hint là docType cụ thể: chấm điểm theo số anchor (so khớp bỏ dấu+space),
  loại bỏ ứng viên nếu dính `excludes` (anti-anchor cho look-alike).
"""
from __future__ import annotations

import re
from typing import Any

from app.extract.textutil import key
from app.plugins.manager import PluginManager

FAMILIES = {"cmnd", "cccd"}


class RuleClassifier:
    def __init__(self, plugins: PluginManager) -> None:
        self.plugins = plugins
        self.known = {m.doc_type for m in plugins.all()}

    def classify(self, lines: list[Any], hint: str | None = None) -> tuple[str, float]:
        text = key(" ".join(getattr(l, "text", "") for l in lines))

        # Hint thô theo họ → detect loại con trong họ.
        if hint in FAMILIES:
            cands = [m for m in self.plugins.all() if m.family == hint]
            if not cands:
                return "unknown", 0.0
            if hint == "cmnd":
                return self._classify_cmnd(cands, lines)
            return self._score(cands, text)

        # Hint là docType cụ thể hợp lệ → tin tưởng.
        if hint and hint in self.known:
            return hint, 0.95

        # Không hint → chấm điểm toàn bộ; nếu ra CMND thì tinh chỉnh theo độ dài số.
        dt, conf = self._score(self.plugins.all(), text)
        if dt in ("cmnd_9", "cmnd_12"):
            return self._classify_cmnd(
                [m for m in self.plugins.all() if m.family == "cmnd"], lines
            )
        return dt, conf

    def _classify_cmnd(self, cands: list, lines: list[Any]) -> tuple[str, float]:
        """CMND: có dãy ≥12 số → cmnd_12; ngược lại cmnd_9 (fallback, theo ưu tiên).
        Bền với OCR sai số 9 (không cần đọc đúng đủ 9 số, chỉ cần VẮNG dãy 12)."""
        by_type = {m.doc_type: m for m in cands}
        has12 = self._has_digit_run(lines, 12)
        pick = "cmnd_12" if (has12 and "cmnd_12" in by_type) else "cmnd_9"
        if pick not in by_type:
            pick = next(iter(by_type), "unknown")
        return (pick, 0.9 if has12 else 0.7) if pick != "unknown" else ("unknown", 0.0)

    @staticmethod
    def _has_digit_run(lines: list[Any], n: int) -> bool:
        for l in lines:
            cleaned = re.sub(r"[ .\-]", "", getattr(l, "text", ""))
            if any(len(run) >= n for run in re.findall(r"\d+", cleaned)):
                return True
        return False

    def _score(self, cands: list, text: str) -> tuple[str, float]:
        best, best_score = None, 0
        for m in cands:
            if any(key(ex) and key(ex) in text for ex in m.excludes):
                continue  # dính anti-anchor → loại
            score = sum(1 for a in m.anchors if key(a) and key(a) in text)
            if score > best_score:
                best, best_score = m.doc_type, score
        if best and best_score > 0:
            return best, min(0.99, 0.6 + 0.2 * best_score)
        return "unknown", 0.0
