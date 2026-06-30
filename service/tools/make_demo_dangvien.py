"""Render một ảnh Thẻ Đảng viên giả lập (tiếng Việt) để test OCR thật khi chưa có
ảnh chụp. KHÔNG phải dữ liệu thật — chỉ để kiểm chứng đường OCR→bóc tách.

    python -m tools.make_demo_dangvien the-dang-vien.jpg
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def build(path: str) -> None:
    W, H = 760, 520
    img = Image.new("RGB", (W, H), (250, 248, 240))
    d = ImageDraw.Draw(img)
    title_f = ImageFont.truetype(FONT, 30)
    f = ImageFont.truetype(FONT, 22)

    d.text((W / 2, 30), "THẺ ĐẢNG VIÊN", font=title_f, fill=(180, 0, 0), anchor="mm")

    LX, VX = 40, 250  # cột nhãn, cột giá trị
    rows = [
        ("Số", "83.060977", 95),
        ("Họ và tên", "NGUYỄN THÙY GIANG", 145),
        ("Sinh ngày", "24 - 09 - 1992", 190),
        ("Quê quán", "X. Tân Triều,", 235),
        ("Vào Đảng ngày", "19 - 05 - 2023", 320),
        ("Chính thức ngày", "19 - 05 - 2024", 360),
        ("Nơi cấp thẻ", "Đảng bộ Khối", 405),
    ]
    for label, value, y in rows:
        d.text((LX, y), label, font=f, fill=(0, 0, 0))
        d.text((VX, y), value, font=f, fill=(0, 0, 0))

    # dòng wrap của Quê quán và Nơi cấp thẻ
    d.text((VX, 270), "H. Thanh Trì, TP. Hà Nội", font=f, fill=(0, 0, 0))
    d.text((VX, 440), "các cơ quan Trung ương", font=f, fill=(0, 0, 0))
    # ngày cấp dạng câu
    d.text((W / 2, 490), "Ngày 07 tháng 11 năm 2024", font=f, fill=(0, 0, 0), anchor="mm")

    img.save(path, "JPEG", quality=92)
    print("Đã tạo", path)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "the-dang-vien.jpg")
