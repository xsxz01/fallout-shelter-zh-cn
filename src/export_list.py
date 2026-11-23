#!/usr/bin/env python3
"""Export the full translation list used by build_patch.py to CSV."""
import csv, json, re

from project_paths import CACHE, LIST_CSV, ORIGINAL, OVERRIDES
import build_patch as bp

d = json.load(open(ORIGINAL, encoding="utf-8"))
cache = json.load(open(CACHE, encoding="utf-8"))
ov = json.load(open(OVERRIDES, encoding="utf-8"))

def polish(zh):
    return (zh.replace("传奇", "传说").replace("......", "……")
              .replace("食尸鬼", "尸鬼").replace("死亡爪", "死爪")
              .replace("监工", "监督者").replace("刺激包", "治疗针")
              .replace("RadAways", "消辐宁").replace("StimPacks", "治疗针")
              .replace("StimPack", "治疗针").replace("RadAway", "消辐宁")
              .replace("盔甲", "护甲").replace("Junk", "废料"))

rows, counts = [], {}
for i, t in enumerate(d["mTerms"], 1):
    key, en = t["Term"], t["Languages"][0]
    if key in ov:
        zh, src = ov[key], "人工UI覆盖"
    elif bp.SHORT_MAP.get(en.strip().upper()):
        zh, src = bp.SHORT_MAP[en.strip().upper()], "术语表"
    elif cache.get(en):
        zh, src = polish(cache[en]), "机翻+术语处理"
    elif not en.strip():
        zh, src = "", "原文为空"
    elif not re.search(r"[A-Za-z]", en):
        zh, src = en, "非英文，保留"
    else:
        zh, src = en, "未翻译，保留英文"
    counts[src] = counts.get(src, 0) + 1
    rows.append([i, key, en, zh, src])

out = LIST_CSV
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["序号", "Term Key", "英文原文", "中文译文", "来源"])
    w.writerows(rows)
print("wrote", out, "rows", len(rows), counts)
