#!/usr/bin/env python3
"""Generate transparent lower-third overlays from edit_plan.json."""
import json, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FONT = r"C:/Windows/Fonts/msyhbd.ttc"
ACCENT = (143, 224, 138, 255)
BG = (10, 14, 10, 210)
TEXT = (214, 224, 214, 255)
MUTED = (140, 153, 140, 255)

def font(size):
    return ImageFont.truetype(FONT, size, index=0)

def main():
    plan = json.load(open("edit_plan.json", encoding="utf-8"))
    os.makedirs("overlays", exist_ok=True)
    for sc in plan["scenes"]:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        text = sc.get("overlay", "")
        if not text:
            continue
        f = font(28)
        b = d.textbbox((0, 0), text, font=f)
        tw, th = b[2] - b[0], b[3] - b[1]
        x, y = 80, 840
        d.rounded_rectangle([x, y, x + tw + 40, y + th + 24], radius=3, fill=BG, outline=ACCENT, width=2)
        d.rectangle([x, y, x + 6, y + th + 28], fill=ACCENT)
        d.text((x + 20, y + 10), text, font=f, fill=TEXT)
        img.save(f"overlays/{sc['id']}.png")
    print("overlays written")

if __name__ == "__main__":
    main()
