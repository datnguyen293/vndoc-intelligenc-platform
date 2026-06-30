"""CLI: nắn một ảnh hoặc cả thư mục. Chạy offline.

    python -m rectifier in.jpg out.jpg
    python -m rectifier ./anh_vao ./anh_ra --preset document --recursive
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rectifier import Rectifier, available_presets
from rectifier.config import preset as build_preset

_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def _iter_images(root: Path, recursive: bool):
    it = root.rglob("*") if recursive else root.glob("*")
    return sorted(p for p in it if p.suffix.lower() in _EXTS)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rectifier",
        description="Nắn ảnh chụp nghiêng/méo/xoay về chữ nhật thẳng hàng (offline).",
    )
    ap.add_argument("src", help="File ảnh hoặc thư mục đầu vào")
    ap.add_argument("dst", help="File ảnh hoặc thư mục đầu ra")
    ap.add_argument("--preset", default="general", choices=available_presets(),
                    help="Preset cấu hình (mặc định: general)")
    ap.add_argument("--recursive", action="store_true", help="Quét thư mục con")
    ap.add_argument("--out-long", type=int, default=None,
                    help="Giới hạn cạnh dài output (px)")
    ap.add_argument("--quiet", action="store_true", help="Bớt log")
    args = ap.parse_args(argv)

    overrides = {}
    if args.out_long is not None:
        overrides["out_long"] = args.out_long
    rectifier = Rectifier(build_preset(args.preset, **overrides))

    src, dst = Path(args.src), Path(args.dst)
    from PIL import Image

    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        files = _iter_images(src, args.recursive)
        if not files:
            print(f"Không tìm thấy ảnh trong {src}", file=sys.stderr)
            return 1
        ok = 0
        for f in files:
            rel = f.relative_to(src)
            out_path = dst / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                res = rectifier.rectify(Image.open(f))
                res.image.save(out_path)
                ok += 1
                if not args.quiet:
                    tag = "nắn" if res.found else "giữ nguyên"
                    print(f"[{tag}] {rel}  ({sum(res.timings.values()):.0f} ms)")
            except Exception as exc:  # noqa: BLE001
                print(f"[lỗi] {rel}: {exc}", file=sys.stderr)
        print(f"Xong: {ok}/{len(files)} ảnh → {dst}")
        return 0 if ok else 1

    # file đơn
    if not src.exists():
        print(f"Không tồn tại: {src}", file=sys.stderr)
        return 1
    if dst.suffix == "":  # dst là thư mục → giữ tên file gốc
        dst.mkdir(parents=True, exist_ok=True)
        dst = dst / src.name
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
    res = rectifier.rectify(Image.open(src))
    res.image.save(dst)
    if not args.quiet:
        tag = "nắn" if res.found else "giữ nguyên"
        print(f"[{tag}] {src.name} → {dst}  ({sum(res.timings.values()):.0f} ms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
