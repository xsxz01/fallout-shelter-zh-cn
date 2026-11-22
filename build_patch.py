#!/usr/bin/env python3
"""Build the Chinese localization bundle for Fallout Shelter 2.7.0.

Reads the original game bundle, applies translations from translations_cache.json,
replaces the seven embedded fonts with a CJK-capable subset, and writes a new
data.unity3d.
"""
import json, os, re, sys, time
import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.helpers.TypeTreeHelper import read_value, write_typetree, TypeTreeConfig
from UnityPy.streams import EndianBinaryWriter

WORK = os.path.dirname(os.path.abspath(__file__))
GAMEDIR = r"D:/Program Files (x86)/Steam/steamapps/common/Fallout Shelter"
SRC = os.path.join(GAMEDIR, r"FalloutShelter_Data/data.unity3d.en.bak")
OUT = os.path.join(WORK, "patch_data.unity3d")
CACHE = os.path.join(WORK, "translations_cache.json")
FONT = os.path.join(WORK, "simhei_fixed.ttf")
REPORT = os.path.join(WORK, "build_report.json")
OVERRIDES = os.path.join(WORK, "overrides.json")

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
LANG_NAME = "English"
LANG_CODE = "En-Us"

def load_language(env):
    x = env.file.files["resources.assets"]
    o = x.objects[20953]
    node = o.generate_monobehaviour_node()

    def fix(n):
        # Unity aligns after m_Enabled; the generated tree omits that flag.
        if n.m_Type == "UInt8" and n.m_Name == "m_Enabled":
            n.m_MetaFlag = 0x4000
        # The generator labels List<T>/string[] nodes by element type; make them vectors.
        arr = [c for c in n.m_Children if c.m_Type == "Array" and c.m_Name == "Array"]
        if arr and arr[0].m_Children[1].m_Type != "char":
            n.m_Type = "vector"
        for c in n.m_Children:
            fix(c)

    fix(node)
    o.reset()
    d = read_value(node, o.reader, TypeTreeConfig(True, x, False))
    return x, o, node, d

def main():
    t0 = time.time()
    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)
    with open(OVERRIDES, encoding="utf-8") as f:
        overrides = json.load(f)
    with open(FONT, "rb") as f:
        font_data = f.read()
    if not font_data.startswith(b"\x00\x01\x00\x00"):
        raise SystemExit("cn_font.ttf is not a TrueType file")

    gen = TypeTreeGenerator("6000.0.58f2")
    gen.load_local_game(GAMEDIR)
    env = UnityPy.load(SRC)
    env.typetree_generator = gen

    x, o, node, d = load_language(env)
    terms = d["mTerms"]
    missing, changed, used_overrides = [], 0, set()

    def polish(zh):
        return (zh.replace("传奇", "传说")
                  .replace("......", "……")
                  .replace("食尸鬼", "尸鬼")
                  .replace("死亡爪", "死爪")
                  .replace("监工", "监督者")
                  .replace("刺激包", "治疗针")
                  .replace("RadAways", "消辐宁")
                  .replace("StimPacks", "治疗针")
                  .replace("StimPack", "治疗针")
                  .replace("RadAway", "消辐宁")
                  .replace("盔甲", "护甲")
                  .replace("Junk", "废料"))

    for t in terms:
        src = t["Languages"][0]
        key = t["Term"]
        if key in overrides:
            t["Languages"][0] = overrides[key]
            t["Flags"][0] = 0
            used_overrides.add(key)
            changed += 1
            continue
        zh = SHORT_MAP.get(src.strip().upper()) or cache.get(src)
        if zh:
            t["Languages"][0] = polish(zh)
            t["Flags"][0] = 0
            changed += 1
        elif src and src.strip() and re.search(r"[A-Za-z]", src):
            missing.append(src)

    # Keep the original language name/code. The slot's text is Chinese, and
    # this guarantees LocalizationManager/FontManager resolve language index 0.
    d["mLanguages"][0]["Name"] = LANG_NAME
    d["mLanguages"][0]["Code"] = LANG_CODE

    w = EndianBinaryWriter(endian="<")
    write_typetree(d, node, w, x)
    o.set_raw_data(w.bytes)

    fonts = []
    for obj in env.objects:
        if obj.type.name != "Font":
            continue
        fo = obj.read()
        fo.m_FontData = list(font_data)
        fo.m_FontNames = ["SimHei"]
        fo.m_Ascent = 13.75
        fo.m_Descent = -2.25
        fo.m_LineSpacing = 20.0
        obj.save_typetree(fo)
        fonts.append(fo.m_Name)

    # FontManager's per-language custom fonts are ASCII-only bitmap atlases.
    # Clearing them makes UILabel use the dynamic Font assets above.
    def read_mono(asset_file, path_id):
        ob = asset_file.objects[path_id]
        nd = ob.generate_monobehaviour_node()

        def fix(n):
            if n.m_Type == "UInt8" and n.m_Name == "m_Enabled":
                n.m_MetaFlag = 0x4000
            arr = [c for c in n.m_Children
                   if c.m_Type == "Array" and c.m_Name == "Array"]
            if arr and arr[0].m_Children[1].m_Type != "char":
                n.m_Type = "vector"
            for c in n.m_Children:
                fix(c)

        fix(nd)
        ob.reset()
        return read_value(nd, ob.reader, TypeTreeConfig(True, asset_file, False)), nd, ob

    for path_id in (20963, 20964):
        fm, nd, ob = read_mono(x, path_id)
        for fl in fm["m_fontsLists"]:
            fl["m_customFonts"] = []
        w = EndianBinaryWriter(endian="<")
        write_typetree(fm, nd, w, x)
        ob.set_raw_data(w.bytes)

    blob = env.file.save(packer="original")
    with open(OUT, "wb") as f:
        f.write(blob)
    report = {
        "terms": len(terms),
        "changed": changed,
        "missing": missing,
        "fonts": fonts,
        "font_data": os.path.basename(FONT),
        "custom_fonts": "cleared",
        "overrides": len(used_overrides),
        "unused_overrides": sorted(set(overrides) - used_overrides),
        "bundle_bytes": len(blob),
        "seconds": round(time.time() - t0, 1),
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "missing"},
                     ensure_ascii=False, indent=1))
    print("missing translations:", len(missing))
    for s in missing[:20]:
        print("  MISS", repr(s[:120]))

if __name__ == "__main__":
    main()
