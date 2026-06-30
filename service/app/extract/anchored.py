"""Bộ trích xuất label-anchored (DOC-05 §4.4, DOC-06 S6-S8).

Đầu vào: danh sách OcrLine (text + vị trí) + manifest. Tìm nhãn in sẵn rồi lấy giá
trị quanh nhãn theo `take`, chuẩn hóa + validate → {field: FieldValue}.
Không cần model train (ADR-012) — chỉ luật hình học + chuỗi.
"""
from __future__ import annotations

import re

from app.extract import dates
from app.extract.normalize import apply_normalizers, norm_sex
from app.extract.textutil import clean_token as _clean_token
from app.extract.textutil import key as _label_key
from app.extract.validate import cross_field_checks, run_checks, validate_field
from app.models.response import FieldValue
from app.ocr.types import OcrLine
from app.plugins.contract import FieldSpec, Manifest

_MERGE_CAP = 1     # số dòng "xuống dòng" gộp tối đa cho 1 giá trị (địa chỉ wrap)
_NOISE_CONF = 0.6  # box confidence dưới mức này coi là nhiễu/watermark khi chọn giá trị


def _lev(a: str, b: str) -> int:
    """Khoảng cách Levenshtein (đủ nhỏ cho chuỗi nhãn ngắn)."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _prefix_match(ftokens: list[str], label_key: str) -> int | None:
    """Số token đầu của dòng khớp với nhãn (gộp không space, chịu ≤1 lỗi nếu nhãn dài).

    Trả k = số token tiêu thụ làm nhãn, hoặc None nếu không khớp.
    """
    acc = ""
    for i, tok in enumerate(ftokens):
        acc += tok
        if acc == label_key:
            return i + 1
        if len(label_key) >= 5 and abs(len(acc) - len(label_key)) <= 1 and _lev(acc, label_key) <= 1:
            return i + 1
        # nhãn dài là TIỀN TỐ của token dính (vd OCR gộp "sinh"+"Date"→"sinhDate")
        if len(label_key) >= 5 and acc.startswith(label_key):
            return i + 1
        if len(acc) > len(label_key) + 1:
            break
    return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def _same_row(a: OcrLine, b: OcrLine) -> bool:
    return abs(a.cy - b.cy) <= 0.6 * max(a.h, b.h)


def _overlap_x(line: OcrLine, x1: float, x2: float) -> bool:
    return line.x < x2 and line.x2 > x1


def _after_colon(text: str) -> str | None:
    if ":" in text:
        return text.split(":", 1)[1].strip() or None
    return None


def _has_vietnamese(text: str) -> bool:
    """Có ký tự chữ ngoài ASCII (dấu tiếng Việt: Ễ, Ủ, đ...) — phân biệt với watermark ASCII."""
    return any(ord(c) > 127 and c.isalpha() for c in text)


class LabelAnchoredExtractor:
    def extract(
        self, lines: list[OcrLine], manifest: Manifest, structured: dict[str, str]
    ) -> tuple[dict[str, FieldValue], list[str]]:
        labels_all = [lb for f in manifest.fields for lb in f.labels]
        used: set[int] = set()
        fields: dict[str, FieldValue] = {}
        warnings: list[str] = []

        for spec in manifest.fields:
            # 1) Ưu tiên nguồn structured (QR/MRZ) nếu có
            if "structured" in spec.source and spec.name in structured:
                value = structured[spec.name]
                value = self._post(value, spec)
                fields[spec.name] = FieldValue(value=value, confidence=0.97, source="structured")
                warnings += validate_field(value, spec) + run_checks(value, spec)
                continue

            # 2) OCR label-anchored, fallback theo mẫu regex nếu không thấy nhãn
            taken = self._take(lines, spec, labels_all, used)
            # Trường có regex mạnh (idNumber...): nếu giá trị bám-nhãn dính nhiễu/nhãn EN
            # song ngữ → KHÔNG khớp regex, thử token khớp regex trong các dòng (OCR dính).
            rgx = spec.validate.get("regex")
            if rgx and not self._matches_regex(taken, spec, rgx):
                fb = self._pattern_fallback(lines, spec, used)
                if fb is not None:
                    taken = fb
            if taken is None:
                taken = self._pattern_fallback(lines, spec, used)
            if taken is None:
                fields[spec.name] = FieldValue(value=None, confidence=0.0, source="ocr")
                if spec.required:
                    warnings.append(f"{spec.name}_thieu")
                continue

            raw_text, conf, consumed = taken
            for ln in consumed:
                used.add(id(ln))

            value = self._post(raw_text, spec)
            raw = raw_text if raw_text != value else None
            fields[spec.name] = FieldValue(
                value=value or None,
                confidence=round(conf, 2) if value else 0.0,
                source="ocr",
                raw=raw,
            )
            warnings += validate_field(value, spec) + run_checks(value, spec)

        warnings += cross_field_checks(fields, manifest.cross_checks)
        return fields, warnings

    # --- post-process: ép kiểu + normalize (DOC-08 §2) ---
    def _post(self, text: str, spec: FieldSpec) -> str:
        value = text.strip()
        if spec.type == "date":
            value = dates.to_iso(value) or value
        elif spec.type == "sex":
            value = norm_sex(value)
        value = apply_normalizers(value, spec.normalize)
        return value

    def _matches_regex(self, taken, spec, rgx) -> bool:
        """Giá trị đã lấy (taken) sau _post có khớp regex của trường không."""
        if taken is None:
            return False
        try:
            return bool(re.fullmatch(rgx, self._post(taken[0], spec) or ""))
        except re.error:
            return True  # regex hỏng → đừng ép fallback

    # --- fallback: trường có regex mạnh nhưng không thấy nhãn ---
    def _pattern_fallback(self, lines, spec, used):
        rgx = spec.validate.get("regex")
        if not rgx:
            return None
        try:
            pat = re.compile(rgx)
        except re.error:
            return None
        for ln in lines:
            if id(ln) in used:
                continue
            # (a) cả dòng đã normalize (gộp số bị OCR tách space, vd "0101 1400 0119").
            cand = self._post(ln.text, spec)
            if cand and pat.fullmatch(cand):
                return cand, ln.confidence, [ln]
            # (b) từng token trong dòng — OCR hay dính tiền tố/nhiễu (vd BHYT
            #     "1855 0111077012" → bắt token đúng độ dài "0111077012").
            for tok in ln.text.split():
                c = self._post(tok, spec)
                if c and pat.fullmatch(c):
                    return c, ln.confidence, [ln]
        return None

    # --- chọn giá trị quanh nhãn theo `take` ---
    def _take(self, lines, spec, labels_all, used):
        take = spec.take

        if take == "vn_date_phrase":
            for ln in lines:
                if id(ln) in used:
                    continue
                if dates.find_date_phrase(ln.text):
                    return ln.text, ln.confidence, [ln]
            return None

        if take == "vn_place_orphan":
            # Có nhãn (ảnh rõ) → lấy như right_of_label_or_below.
            found = self._find_label(lines, spec.labels, used)
            if found:
                label_line, inline = found
                if inline:
                    return inline, label_line.confidence, [label_line]
                belows = self._below(lines, label_line, label_line.x, label_line.x2, used, labels_all)
                if belows:
                    return " ".join(b.text for b in belows), belows[0].confidence, [label_line] + belows
            # Nhãn KHÔNG được OCR (thẻ giấy ép cũ): dòng địa danh mồ côi — có chữ tiếng Việt,
            # ≥2 từ, nằm DƯỚI dòng ngày sinh, chưa dùng, không phải ngày/nhãn.
            date_ys = [l.y for l in lines if dates.find_date(l.text)]
            if not date_ys:
                return None
            ymax = max(date_ys)
            for l in sorted((x for x in lines if id(x) not in used and x.y > ymax),
                            key=lambda x: x.y):
                if (not dates.find_date(l.text) and not self._is_label(l, labels_all)
                        and _has_vietnamese(l.text) and len(l.text.split()) >= 2):
                    return l.text, l.confidence, [l]
            return None

        found = self._find_label(lines, spec.labels, used)
        if found is None:
            return None
        label_line, inline = found

        if take == "after_colon":
            val = _after_colon(label_line.text) or inline
            return (val, label_line.confidence, [label_line]) if val else None

        if take == "trailing_digit":
            m = re.search(r"(\d)\s*$", label_line.text)
            return (m.group(1), label_line.confidence, [label_line]) if m else None

        right = self._right_neighbor(lines, label_line, used, prefer_vi=(spec.type == "text_vi"))

        if take == "date_after_label":
            ac = _after_colon(label_line.text)
            for cand in (ac, inline):
                if cand and dates.find_date(cand):
                    return cand, label_line.confidence, [label_line]
            # Quét MỌI box bên phải cùng hàng để tìm ngày (bỏ qua box nhiễu chen giữa).
            for nb in self._right_row(lines, label_line, used):
                if dates.find_date(nb.text):
                    return nb.text, nb.confidence, [label_line, nb]
            # Layout song ngữ xếp dọc (Căn cước 2024): ngày nằm DƯỚI nhãn → quét vài dòng dưới.
            below = sorted(
                (l for l in lines if id(l) not in used and l is not label_line
                 and l.cy > label_line.y2 - 0.3 * label_line.h
                 and _overlap_x(l, label_line.x, label_line.x2)),
                key=lambda l: l.y,
            )
            for b in below[:3]:
                if dates.find_date(b.text):
                    return b.text, b.confidence, [label_line, b]
            return None

        if take == "smart":
            # Lấy giá trị: sau ':' (hoặc phần dư) → bên phải → ngay dưới.
            consumed = [label_line]
            ac = _after_colon(label_line.text) or inline
            if ac:
                value = ac
            elif right:
                value = right.text
                consumed.append(right)
            else:
                belows = self._below(lines, label_line, label_line.x, label_line.x2, used, labels_all)
                if not belows:
                    return None
                value = belows[0].text
                consumed.append(belows[0])
            # multiline (vd địa chỉ wrap): gộp dòng dưới, BỎ dòng ngày/nhãn.
            # Cột tìm = từ nhãn tới mép phải GIÁ TRỊ (dòng dưới hay thụt phải, lệch cột nhãn).
            if spec.multiline:
                col_x2 = max([label_line.x2] + [c.x2 for c in consumed if c is not label_line])
                for b in self._below(lines, label_line, label_line.x, col_x2, used, labels_all):
                    if b in consumed or self._is_label(b, labels_all):
                        continue
                    if dates.find_date(b.text) or dates.find_date_phrase(b.text):
                        continue
                    value += " " + b.text
                    consumed.append(b)
            return value, label_line.confidence, consumed

        if take == "right_of_label":
            if inline:
                return inline, label_line.confidence, [label_line]
            if right:
                return right.text, right.confidence, [label_line, right]
            return None

        if take == "below_label":
            anchor = label_line
            col1, col2 = label_line.x, label_line.x2
            belows = self._below(lines, anchor, col1, col2, used, labels_all)
            if belows:
                txt = " ".join(b.text for b in belows)
                return txt, belows[0].confidence, [label_line] + belows
            return None

        if take == "after_colon_or_below":
            val = _after_colon(label_line.text) or inline
            if val:
                return val, label_line.confidence, [label_line]
            belows = self._below(lines, label_line, label_line.x, label_line.x2, used, labels_all)
            if belows:
                return " ".join(b.text for b in belows), belows[0].confidence, [label_line] + belows
            return None

        if take == "right_of_label_or_below":
            base = inline
            base_line = label_line
            consumed = [label_line]
            if not base and right:
                base = right.text
                base_line = right
                consumed.append(right)
            if not base:
                # không có bên phải → lấy ngay dưới
                belows = self._below(lines, label_line, label_line.x, label_line.x2, used, labels_all)
                if belows:
                    return " ".join(b.text for b in belows), belows[0].confidence, [label_line] + belows
                return None
            # gộp dòng wrap (cùng cột với giá trị)
            belows = self._below(lines, base_line, base_line.x, base_line.x2, used, labels_all)
            parts = [base] + [b.text for b in belows]
            return " ".join(parts), base_line.confidence, consumed + belows

        return None

    # --- helpers hình học ---
    def _find_label(self, lines, labels, used):
        keys = [_label_key(lb) for lb in labels if _label_key(lb)]
        for ln in lines:
            if id(ln) in used:
                continue
            # Tách theo khoảng trắng VÀ "/" để khớp nhãn song ngữ ("Số/No", "Họ tên/Full name")
            words = re.findall(r"[^\s/]+", ln.text)
            ftokens = [_clean_token(w) for w in words]
            k = self._match_label_span(ftokens, keys)
            if k:
                remainder = " ".join(words[k:]).lstrip(" :/")
                return ln, (remainder or None)
        return None

    @staticmethod
    def _match_label_span(ftokens, keys) -> int:
        """Khớp nhãn đầu rồi NUỐT TIẾP các phần nhãn liền sau (vd phần EN song ngữ),
        để 'Full name:' không bị nhầm thành giá trị. Trả số token tiêu thụ làm nhãn."""
        first = None
        for key in keys:
            kk = _prefix_match(ftokens, key)
            if kk is not None:
                first = kk
                break
        if first is None:
            return 0
        k = first
        while True:
            ext = None
            for key in keys:
                kk = _prefix_match(ftokens[k:], key)
                if kk is not None:
                    ext = kk
                    break
            if not ext:
                break
            k += ext
        return k

    def _right_neighbor(self, lines, label, used, prefer_vi=False):
        cands = self._right_row(lines, label, used)
        if not cands:
            return None
        # Ưu tiên box "sạch" (confidence cao) — bỏ qua watermark/nhiễu chen giữa.
        pool = [c for c in cands if c.confidence >= _NOISE_CONF] or cands
        # text_vi: ưu tiên box có DẤU tiếng Việt (watermark "DRIVER'S LICENSE"... là ASCII).
        if prefer_vi:
            vi = [c for c in pool if _has_vietnamese(c.text)]
            if vi:
                pool = vi
        return pool[0]

    def _right_row(self, lines, label, used):
        """Tất cả box bên phải nhãn, cùng hàng, sắp theo x (gần → xa).

        Ngưỡng x nới tới `x2 - 1.0*h`: nhãn ngắn (vd "Họ tên") + giá trị box rộng có thể
        bắt đầu hơi chồng mép phải nhãn do OCR; vẫn chặn box nằm hẳn bên trái nhãn.
        """
        cands = [
            l for l in lines
            if id(l) not in used and l is not label
            and _same_row(label, l) and l.x >= label.x2 - 1.0 * label.h
        ]
        return sorted(cands, key=lambda l: l.x)

    def _below(self, lines, anchor, col1, col2, used, labels_all):
        cands = sorted(
            (l for l in lines
             if id(l) not in used and l is not anchor
             and l.cy > anchor.y2 - 0.3 * anchor.h
             and _overlap_x(l, col1, col2)),
            key=lambda l: l.y,
        )
        out: list[OcrLine] = []
        prev_y2 = anchor.y2
        for c in cands:
            if len(out) >= _MERGE_CAP:
                break
            if self._is_label(c, labels_all):
                break
            if (c.y - prev_y2) > 1.4 * anchor.h:
                break
            out.append(c)
            prev_y2 = c.y2
        return out

    def _is_label(self, line, labels_all) -> bool:
        ftokens = [_clean_token(w) for w in re.findall(r"[^\s/]+", line.text)]
        return any(_prefix_match(ftokens, _label_key(lb)) is not None
                   for lb in labels_all if _label_key(lb))
