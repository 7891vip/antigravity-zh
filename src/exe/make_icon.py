# -*- coding: utf-8 -*-
"""生成安装器图标（蓝底圆角 + 白色「中」），输出多尺寸 ico。"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=56, fill=(47, 113, 227, 255))

font = None
for path, idx in ((r"C:\Windows\Fonts\msyhbd.ttc", 0), (r"C:\Windows\Fonts\msyh.ttc", 0),
                  (r"C:\Windows\Fonts\simhei.ttf", 0)):
    if os.path.exists(path):
        try:
            font = ImageFont.truetype(path, 150, index=idx)
            break
        except Exception:
            continue

text = "中"
if font is None:
    font = ImageFont.load_default()

box = d.textbbox((0, 0), text, font=font)
w, h = box[2] - box[0], box[3] - box[1]
d.text(((SIZE - w) / 2 - box[0], (SIZE - h) / 2 - box[1]), text, font=font, fill=(255, 255, 255, 255))

img.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon ->", OUT, os.path.getsize(OUT), "bytes")
