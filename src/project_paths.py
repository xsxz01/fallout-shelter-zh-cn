#!/usr/bin/env python3
"""Central project paths for the Fallout Shelter zh-CN toolchain."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CONFIG = ROOT / "config"
RESOURCES = ROOT / "resources"
FONTS = RESOURCES / "fonts"
DOCS = ROOT / "docs"
CHANGELOGS = ROOT / "changelogs"
SCRIPTS = ROOT / "scripts"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

GAME_DIR = Path(os.environ.get("FS_GAME_DIR", r"D:/Program Files (x86)/Steam/steamapps/common/Fallout Shelter"))
GAME_DATA = GAME_DIR / "FalloutShelter_Data" / "data.unity3d"
GAME_BACKUP = GAME_DIR / "FalloutShelter_Data" / "data.unity3d.en.bak"
PATCH_DIR = GAME_DIR / "汉化补丁"

ORIGINAL = RESOURCES / "langsource_orig.json"
CACHE = RESOURCES / "translations_cache.json"
LIST_CSV = RESOURCES / "翻译清单.csv"
FONT_CHARS = RESOURCES / "font_chars.txt"
FONT_FIXED = FONTS / "simhei_fixed.ttf"
FONT_STRIPPED = FONTS / "simhei_stripped.ttf"

OVERRIDES = CONFIG / "overrides.json"
BRACE_MAP = CONFIG / "brace_map.json"
VERSION_FILE = CONFIG / "version.txt"
INSTALLER_THEME = CONFIG / "installer_theme.json"

PATCH_DATA = BUILD / "patch_data.unity3d"
BUILD_REPORT = BUILD / "build_report.json"
