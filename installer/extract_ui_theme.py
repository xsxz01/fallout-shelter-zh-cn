#!/usr/bin/env python3
"""Extract a theme summary from the game client UI for the installer."""
import json, os
from collections import Counter
from PIL import Image
import UnityPy

W = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(W)
GAME = os.path.join(ROOT, "GameBackup_2.7.0_original", "FalloutShelter_Data", "data.unity3d")
SCREEN = os.path.join(W, "source_ui.png")
OUT = os.path.join(W, "theme.json")

def hexc(rgb):
    return "#%02X%02X%02X" % rgb

def palette():
    if not os.path.exists(SCREEN):
        return {}
    im = Image.open(SCREEN).convert("RGB").resize((240, 150))
    counts = Counter(im.getdata())
    return {
        "background": hexc(counts.most_common(1)[0][0]),
        "samples": [{"color": hexc(c), "pixels": n} for c, n in counts.most_common(12)],
    }

def fonts_and_terms():
    env = UnityPy.load(GAME)
    fonts = []
    terms = 0
    for o in env.objects:
        if o.type.name == "Font":
            d = o.read()
            fonts.append({"name": d.m_Name, "size": len(d.m_FontData), "names": list(d.m_FontNames)})
        elif o.type.name == "MonoBehaviour":
            b = o.get_raw_data()
            if len(b) > 7_000_000:
                terms += 1
    return fonts, terms

if __name__ == "__main__":
    fonts, terms = fonts_and_terms()
    data = {
        "source": "Fallout Shelter 2.7.0 client UI",
        "screen": os.path.basename(SCREEN),
        "palette": palette(),
        "fonts": fonts,
        "localization_sources": terms,
        "installer": {
            "background": "#0E120E",
            "panel": "#171D17",
            "panel_alt": "#1F261F",
            "line": "#3A4A3A",
            "text": "#D6E0D6",
            "muted": "#8C998C",
            "accent": "#8FE08A",
            "accent_bright": "#C8FFC0",
            "warning": "#FFCC66",
            "danger": "#FF6B5E",
            "heading_font": "Bahnschrift SemiCondensed",
            "mono_font": "Cascadia Mono",
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("wrote", OUT)
    print(json.dumps(data["palette"], indent=1)[:800])
    print("fonts", [f["name"] for f in fonts], "terms", terms)
