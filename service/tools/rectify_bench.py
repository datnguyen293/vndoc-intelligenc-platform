"""Benchmark DocumentRectifier: thời gian/stage trên các ảnh mẫu.

    python -m tools.rectify_bench samples/gplx_pet/*.webp samples/gplx_pet/*.jpeg
"""
from __future__ import annotations

import sys
import time
from collections import defaultdict

from PIL import Image
from rectifier import Rectifier, preset


def main() -> None:
    rect = Rectifier(preset("id_card"))
    agg = defaultdict(float)
    n = 0
    print(f"{'ảnh':40} {'found':6} {'total_ms':9}  stages")
    for path in sys.argv[1:]:
        img = Image.open(path).convert("RGB")
        t = time.perf_counter()
        r = rect.rectify(img)
        total = (time.perf_counter() - t) * 1000
        n += 1
        agg["total"] += total
        for k, v in r.timings.items():
            agg[k] += v
        name = path.split("/")[-1]
        print(f"{name:40} {str(r.found):6} {total:8.1f}  {r.timings}")
    if n:
        print("\n--- trung bình/ảnh (ms) ---")
        for k in sorted(agg):
            print(f"  {k:14}: {agg[k]/n:7.1f}")


if __name__ == "__main__":
    main()
