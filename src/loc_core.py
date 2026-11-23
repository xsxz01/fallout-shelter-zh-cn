#!/usr/bin/env python3
"""Shared data layer for the Fallout Shelter zh-CN editor and exporters."""
import csv, json, os, re

from project_paths import CACHE, LIST_CSV, ORIGINAL, OVERRIDES

SHORT_MAP = {
    "LVL": "等级", "SEC": "秒", "MIN": "分钟", "HRS": "小时", "HR": "小时",
    "RANK": "排名", "RUSH": "加速", "OFF": "关", "ON": "开", "SAVE": "保存",
    "NONE": "无", "TIPS": "提示", "QUIT": "退出", "DIFF": "难度", "PC": "PC",
    "ALL": "全部", "COST": "消耗", "SORT": "排序", "STATUS": "状态",
    "CLAIM": "领取", "BUY": "购买", "SELL": "出售", "JOB": "工作",
    "TEAM": "队伍", "TIME": "时间", "DATE": "日期", "NAME": "名称",
    "QTY": "数量", "RARE": "稀有", "MAX": "最大", "MEGA": "超级",
    "XP": "XP", "HP": "生命", "DEAD": "死亡", "DONE": "完成",
    "OPEN": "打开", "HELP": "帮助", "HERE": "此处", "SEND": "发送",
    "SKIP": "跳过", "SPIN": "旋转", "CLUB": "俱乐部", "BAR": "酒吧",
    "GYM": "健身房", "FOOD": "食物", "PET": "宠物", "PETS": "宠物",
    "JUNK": "废料", "CAPS": "瓶盖", "YES": "是", "NO": "否", "OK": "确定",
    "BACK": "返回", "FLEE": "撤退", "HOLD": "按住", "KEEP": "保留",
    "SHOP": "商店", "CANCEL": "取消", "ACCEPT": "接受", "ATTENTION": "注意",
    "COMPLETED": "已完成", "COMPLETE": "完成", "FINISH": "完成",
}


def polish(zh):
    return (zh.replace("传奇", "传说").replace("......", "……")
              .replace("食尸鬼", "尸鬼").replace("死亡爪", "死爪")
              .replace("监工", "监督者").replace("刺激包", "治疗针")
              .replace("RadAways", "消辐宁").replace("StimPacks", "治疗针")
              .replace("StimPack", "治疗针").replace("RadAway", "消辐宁")
              .replace("盔甲", "护甲").replace("Junk", "废料"))


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def load_terms():
    """Returns (terms, cache, overrides). terms: list of original TermData dicts."""
    data = load_json(ORIGINAL, {})
    return data.get("mTerms", []), load_json(CACHE, {}), load_json(OVERRIDES, {})


def effective(en, key, cache, overrides):
    """Return (chinese, source_label, has_manual_override)."""
    if key in overrides:
        return overrides[key], "人工UI覆盖", True
    short = SHORT_MAP.get(en.strip().upper())
    if short:
        return short, "术语表", False
    if en in cache:
        return polish(cache[en]), "机翻+术语处理", False
    if not en.strip():
        return "", "原文为空", False
    if not re.search(r"[A-Za-z]", en):
        return en, "非英文，保留", False
    return en, "未翻译，保留英文", False


def build_rows():
    terms, cache, overrides = load_terms()
    rows = []
    counts = {}
    for i, t in enumerate(terms, 1):
        en = t["Languages"][0]
        key = t["Term"]
        zh, src, manual = effective(en, key, cache, overrides)
        counts[src] = counts.get(src, 0) + 1
        rows.append({
            "no": i, "key": key, "en": en, "zh": zh, "src": src,
            "manual": manual, "term_type": t.get("TermType", 0),
            "description": t.get("Description", ""),
            "others": t.get("Languages", [])[1:],
        })
    return rows, counts


def export_csv(path=LIST_CSV):
    rows, counts = build_rows()
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["序号", "Term Key", "英文原文", "中文译文", "来源"])
        for r in rows:
            w.writerow([r["no"], r["key"], r["en"], r["zh"], r["src"]])
    return len(rows), counts
