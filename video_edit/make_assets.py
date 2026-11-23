#!/usr/bin/env python3
"""Compose title/endcard/thumbnail using extracted game art."""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pathlib import Path

ROOT = Path(__file__).resolve().parent
G = ROOT / "game_assets"
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

BG = (14, 18, 14)
PANEL = (23, 29, 23)
LINE = (58, 74, 58)
TEXT = (214, 224, 214)
MUTED = (140, 153, 140)
ACCENT = (143, 224, 138)
BRIGHT = (200, 255, 192)
WARN = (255, 204, 102)

CN = r"C:/Windows/Fonts/msyhbd.ttc"
MONO = r"C:/Windows/Fonts/consola.ttf"
HEAD = r"C:/Windows/Fonts/bahnschrift.ttf"

def f(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)

def cover(path, size):
    im = Image.open(path).convert("RGBA")
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    x = (im.width - tw) // 2
    y = (im.height - th) // 2
    return im.crop((x, y, x + tw, y + th))

def composite_bg(size, dim=0.72):
    bg = Image.new("RGBA", size, BG + (255,))
    art = cover(G / "Login_Background.png", size)
    art.putalpha(art.getchannel("A").point(lambda a: int(a * 0.55)))
    bg.alpha_composite(art)
    if dim:
        overlay = Image.new("RGBA", size, (0, 0, 0, int(255 * dim)))
        bg.alpha_composite(overlay)
    # scanlines
    d = ImageDraw.Draw(bg, "RGBA")
    for y in range(0, size[1], 4):
        d.line([(0, y), (size[0], y)], fill=(17, 23, 17, 80), width=1)
    return bg

def cutout(path, height):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    w = round(im.width * height / im.height)
    return im.resize((w, height), Image.LANCZOS)

def logo(path, width):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.LANCZOS)

def corners(d, size, pad=36, length=42):
    w, h = size
    for x, y, sx, sy in [(pad, pad, 1, 1), (w-pad, pad, -1, 1), (pad, h-pad, 1, -1), (w-pad, h-pad, -1, -1)]:
        d.line([(x, y), (x+sx*length, y)], fill=ACCENT + (255,), width=3)
        d.line([(x, y), (x, y+sy*length)], fill=ACCENT + (255,), width=3)

def scanline_texture(img):
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, img.height, 4):
        d.line([(0, y), (img.width, y)], fill=(17, 23, 17, 90), width=1)

# ---------- title 1920x1080 ----------
size = (1920, 1080)
img = composite_bg(size, 0.35)
lg = logo(G / "D_logo_01.png", 190)
img.alpha_composite(lg, (64, 42))
vb = cutout(G / "vaultboy.png", 600)
img.alpha_composite(vb, (1260, 360))
d = ImageDraw.Draw(img)
d.text((120, 300), "辐射：避难所", font=f(CN, 108), fill=TEXT + (255,))
d.text((124, 440), "简体中文补丁", font=f(CN, 60), fill=ACCENT + (255,))
d.text((126, 530), "v1.2.1", font=f(HEAD, 44), fill=WARN + (255,))
d.line([(126, 610), (760, 610)], fill=LINE + (255,), width=2)
d.text((126, 640), "STEAM 2.7.0  ·  一键安装  ·  随时还原", font=f(CN, 30), fill=BRIGHT + (255,))
d.text((64, 1000), "github.com/xsxz01/fallout-shelter-zh-cn", font=f(MONO, 20), fill=MUTED + (255,))
corners(d, size)
img.convert("RGB").save(OUT / "title.png")

# ---------- endcard 1920x1080 ----------
img = composite_bg(size, 0.45)
vb = cutout(G / "vaultboy.png", 440)
img.alpha_composite(vb, (120, 560))
d = ImageDraw.Draw(img)
d.text((760, 300), "感谢观看", font=f(CN, 116), fill=BRIGHT + (255,))
d.text((764, 460), "第十一届计算机系装逼犯", font=f(CN, 42), fill=ACCENT + (255,))
d.text((764, 540), "B站 space.bilibili.com/32159982   ·   GitHub xsxz01/fallout-shelter-zh-cn", font=f(CN, 20), fill=MUTED + (255,))
d.line([(764, 610), (1500, 610)], fill=LINE + (255,), width=2)
d.text((764, 640), "补丁仅用于合法拥有的游戏副本", font=f(CN, 24), fill=WARN + (255,))
corners(d, size)
img.convert("RGB").save(OUT / "endcard.png")

# ---------- thumbnail 1280x720 ----------
tsize = (1280, 720)
img = composite_bg(tsize, 0.30)
lg = logo(G / "D_logo_01.png", 200)
img.alpha_composite(lg, (36, 26))
vb = cutout(G / "vaultboy.png", 460)
img.alpha_composite(vb, (790, 160))
d = ImageDraw.Draw(img)
d.text((44, 160), "Steam 版", font=f(CN, 48), fill=MUTED + (255,))
d.text((40, 220), "有中文了", font=f(CN, 118), fill=ACCENT + (255,))
d.text((46, 380), "2.7.0 汉化补丁", font=f(CN, 38), fill=TEXT + (255,))
d.text((46, 440), "v1.2.1", font=f(HEAD, 30), fill=WARN + (255,))
d.rectangle([0, 0, tsize[0]-1, tsize[1]-1], outline=LINE + (255,), width=2)
img.convert("RGB").save(OUT / "thumbnail.png")
print("assets composed")
