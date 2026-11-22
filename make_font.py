#!/usr/bin/env python3
"""Build a CJK font subset covering GB2312, Latin/Cyrillic, and every translated char."""
import json, os, subprocess, sys
from fontTools.ttLib import TTFont

W = os.path.dirname(os.path.abspath(__file__))
SRC_FONT = r"C:/Windows/Fonts/simhei.ttf"
OUT_FONT = os.path.join(W, "simhei_fixed.ttf")
CHARS_TXT = os.path.join(W, "font_chars.txt")

chars = set()
# GB2312 level 1+2
for hi in range(0xB0, 0xF8):
    for lo in range(0xA1, 0xFF):
        try:
            chars.add(bytes([hi, lo]).decode("gb2312"))
        except UnicodeDecodeError:
            pass
# Latin-1, basic Cyrillic, punctuation, CJK punctuation, fullwidth forms
for a, b in [(0x20, 0x7F), (0xA0, 0x100), (0x400, 0x500), (0x2000, 0x2070),
             (0x3000, 0x3040), (0xFF00, 0xFFF0)]:
    chars |= {chr(c) for c in range(a, b)}
# Everything used by the current language columns (incl. our translations)
d = json.load(open(os.path.join(W, "langsource_orig.json"), encoding="utf-8"))
for t in d["mTerms"]:
    for s in t["Languages"] + t["Languages_Touch"]:
        chars |= set(s)
cache = json.load(open(os.path.join(W, "translations_cache.json"), encoding="utf-8"))
for s in cache.values():
    chars |= set(s)
chars = {c for c in chars if c not in "\r\n\t"}

font = TTFont(SRC_FONT, fontNumber=0)
orig_os2 = font["OS/2"]
orig_ranges = (orig_os2.ulUnicodeRange1, orig_os2.ulUnicodeRange2,
               orig_os2.ulUnicodeRange3, orig_os2.ulUnicodeRange4,
               orig_os2.ulCodePageRange1, orig_os2.ulCodePageRange2)
# Unity 6's legacy font renderer rejects several optional tables / loses CJK bits.
for table in ["vhea", "vmtx", "STAT", "BASE", "GDEF", "GPOS", "GSUB", "DSIG",
              "meta", "LTSH", "VDMX", "hdmx", "cvt ", "fpgm", "prep"]:
    if table in font:
        del font[table]
font.save(os.path.join(W, "simhei_stripped.ttf"))
strip_font = os.path.join(W, "simhei_stripped.ttf")
cmap = set()
for table in font["cmap"].tables:
    cmap |= set(table.cmap.keys())
missing = sorted(c for c in chars if ord(c) not in cmap)
keep = "".join(sorted(c for c in chars if ord(c) in cmap))
open(CHARS_TXT, "w", encoding="utf-8").write(keep)
subprocess.run([sys.executable, "-m", "fontTools.subset", strip_font,
                f"--text-file={CHARS_TXT}", f"--output-file={OUT_FONT}",
                "--no-hinting", "--desubroutinize", "--no-prune-unicode-ranges"],
               check=True)
out = TTFont(OUT_FONT)
os2 = out["OS/2"]
(os2.ulUnicodeRange1, os2.ulUnicodeRange2, os2.ulUnicodeRange3,
 os2.ulUnicodeRange4, os2.ulCodePageRange1, os2.ulCodePageRange2) = orig_ranges
os2.ulCodePageRange1 |= 0x40001
out.save(OUT_FONT)
print("chars", len(chars), "kept", len(keep), "missing", len(missing),
      "font_bytes", os.path.getsize(OUT_FONT))
if missing:
    print("missing chars:", "".join(missing[:200]))
