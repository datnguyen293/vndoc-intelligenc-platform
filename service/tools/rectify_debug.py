"""Nắn 1 ảnh bằng package `rectifier` (preset id_card), lưu các stage + montage.

    python -m tools.rectify_debug samples/gplx_pet/tien-dat-meo.jpeg /tmp/dbg
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rectifier import Rectifier, preset


def _save_debug(stages: dict, out_dir: str) -> list[str]:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    saved, tiles = [], []
    for name, img in stages.items():
        arr = img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        p = d / f"{name}.jpg"
        cv2.imwrite(str(p), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        saved.append(str(p))
        tiles.append((name, arr))
    if tiles:
        tw, rows = 360, []
        for name, arr in tiles:
            t = cv2.resize(arr, (tw, int(arr.shape[0] * tw / arr.shape[1])))
            cv2.putText(t, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            rows.append(t)
        hmax = max(r.shape[0] for r in rows)
        rows = [cv2.copyMakeBorder(r, 0, hmax - r.shape[0], 0, 8, cv2.BORDER_CONSTANT,
                                   value=(255, 255, 255)) for r in rows]
        mp = d / "montage.jpg"
        cv2.imwrite(str(mp), cv2.cvtColor(np.hstack(rows), cv2.COLOR_RGB2BGR))
        saved.append(str(mp))
    return saved


def main() -> None:
    src = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/rectify_debug"
    result = Rectifier(preset("id_card")).rectify(Image.open(src), debug=True)
    print("found:", result.found, "| size:", result.image.size, "| timings:", result.timings)
    for f in _save_debug(result.stages, out_dir):
        print("  saved", f)


if __name__ == "__main__":
    main()
