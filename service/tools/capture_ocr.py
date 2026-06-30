"""Chụp output OCR thật (OcrLine) của các ảnh mẫu → fixture JSON cho test golden.

Chạy 1 lần (cần backend thật, vd VietOCR) để 'đóng băng' text OCR; test golden sau đó
chạy bộ trích xuất trên fixture này mà KHÔNG cần model → bắt hồi quy shared code.

    DIP_OCR_BACKEND=vietocr python -m tools.capture_ocr samples/**/*.jpg ...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from app.cv import build_preprocessors
from app.ocr import create_ocr_engine
from app.settings import settings

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "ocr"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    eng = create_ocr_engine()
    _, rectifier = build_preprocessors(settings.card_detect)  # cùng tiền xử lý như production
    for arg in sys.argv[1:]:
        p = Path(arg)
        img = rectifier.rectify(Image.open(p).convert("RGB"), None)
        lines = eng.recognize(img)
        data = {
            "image": p.name,
            "lines": [
                {"text": l.text, "x": round(l.x, 1), "y": round(l.y, 1),
                 "w": round(l.w, 1), "h": round(l.h, 1), "confidence": round(l.confidence, 4)}
                for l in lines
            ],
        }
        # Tên fixture = <folder docType>__<stem> để tránh trùng (vd thuy-giang ở 2 loại).
        name = f"{p.parent.name}__{p.stem}"
        (OUT / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"saved {name}.json ({len(lines)} lines)")


if __name__ == "__main__":
    main()
