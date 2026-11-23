#!/usr/bin/env python3
"""Extract the few game-art images used by make_assets.py."""
import os
from pathlib import Path
import UnityPy
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "game_assets"
OUT.mkdir(exist_ok=True)

DEFAULT = r"D:/Program Files (x86)/Steam/steamapps/common/Fallout Shelter/FalloutShelter_Data/data.unity3d.en.bak"

def main():
    src = os.environ.get("GAME_BUNDLE", DEFAULT)
    env = UnityPy.load(src)
    wanted = {
        "Login_Background": "Login_Background.png",
        "D_logo_01": "D_logo_01.png",
        "VaultName_Circle": "VaultName_Circle.png",
        "VaultBoy_AnimationsOk_mipmaps": "VaultBoy_AnimationsOk_mipmaps.png",
    }
    found = set()
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        d = o.read()
        if d.m_Name in wanted:
            img = d.image
            if img:
                img.save(OUT / wanted[d.m_Name])
                found.add(d.m_Name)
                print("exported", d.m_Name)
    # Clean thumbs-up Vault Boy cutout (component at x=756..1148, y=104..576)
    sheet = OUT / "VaultBoy_AnimationsOk_mipmaps.png"
    if sheet.exists():
        im = Image.open(sheet).convert("RGBA")
        im.crop((756, 104, 1148, 576)).save(OUT / "vaultboy.png")
        print("cut vaultboy.png")
    print("missing", set(wanted) - found)

if __name__ == "__main__":
    main()
