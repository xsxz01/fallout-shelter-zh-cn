#!/usr/bin/env python3
"""Batch-translate Fallout Shelter English terms to Simplified Chinese.

Writes translations_cache.json mapping original English -> Chinese.
Uses Google's public gtx endpoint via POST batch (multiple q params).
Protects placeholders / markup / glossary terms with [[...]] tokens that
the translator preserves.
"""
import json, os, re, sys, time, random, urllib.parse, urllib.request, urllib.error

from project_paths import CACHE, ORIGINAL
ENDPOINT = "https://translate.googleapis.com/translate_a/t?client=gtx&sl=en&tl=zh-CN"
BATCH = 20
RETRIES = 6

# Longest first. Case-insensitive whole-word matching.
GLOSSARY = [
    ("Overseer's Office", "监督者办公室"),
    ("Brotherhood of Steel", "钢铁兄弟会"),
    ("Bottle & Cappy", "瓶子和盖盖"),
    ("Nuka-Cola Bottler", "核子可乐装瓶室"),
    ("Water Treatment", "净水室"),
    ("Power Generator", "发电室"),
    ("Living Quarters", "宿舍"),
    ("Weapon Workshop", "武器工坊"),
    ("Outfit Workshop", "服装工坊"),
    ("Theme Workshop", "主题工坊"),
    ("Science Lab", "科学实验室"),
    ("Nuclear Reactor", "核反应堆"),
    ("Vault Door", "避难所大门"),
    ("Fitness Room", "健身室"),
    ("Game Room", "游戏室"),
    ("Radio Room", "广播室"),
    ("Vault-Tec", "避难所科技"),
    ("Vault Boy", "避难所男孩"),
    ("Power Armor", "动力装甲"),
    ("RadAway", "消辐宁"),
    ("Stimpak", "治疗针"),
    ("Stimpaks", "治疗针"),
    ("Rad-X", "抗辐宁"),
    ("Nuka-Cola", "核子可乐"),
    ("Mr. Handy", "巧手先生"),
    ("Super Mutant", "超级变种人"),
    ("Deathclaw", "死爪"),
    ("Radscorpion", "辐射蝎"),
    ("Radroach", "辐射蟑螂"),
    ("Lunchbox", "午餐盒"),
    ("Lunchboxes", "午餐盒"),
    ("Wasteland", "废土"),
    ("Overseer", "监督者"),
    ("Dwellers", "居民"),
    ("Dweller", "居民"),
    ("Raiders", "掠夺者"),
    ("Raider", "掠夺者"),
    ("Ghouls", "尸鬼"),
    ("Ghoul", "尸鬼"),
    ("CAPS", "瓶盖"),
    ("Caps", "瓶盖"),
    ("Vaults", "避难所"),
    ("Vault", "避难所"),
    ("Pip-Boy", "哔哔小子"),
    ("S.P.E.C.I.A.L.", "S.P.E.C.I.A.L."),
    ("SPECIAL", "SPECIAL"),
    ("Happiness", "幸福度"),
    ("Health", "生命值"),
    ("Damage Resistance", "伤害抗性"),
    ("Damage", "伤害"),
    ("Strength", "力量"),
    ("Perception", "感知"),
    ("Endurance", "耐力"),
    ("Charisma", "魅力"),
    ("Intelligence", "智力"),
    ("Agility", "敏捷"),
    ("Luck", "幸运"),
    ("Medbay", "医务室"),
    ("Barbershop", "理发店"),
    ("Classroom", "教室"),
    ("RobCo", "罗博科"),
    ("Institute", "学院"),
    ("Enclave", "英克雷"),
]

def protect(text, glossary=True):
    """Return (masked_text, restore_map)."""
    m = {}
    def add(rep, token):
        m[f"[[{token}]]"] = rep
        return f"[[{token}]]"
    # Order matters: square-bracket markup first, before any [[token]] exists.
    text = re.sub(r"\[[^\[\]]*\]", lambda x: add(x.group(0), f"T{len(m)}"), text)
    # {placeholders}
    text = re.sub(r"\{[^{}]*\}", lambda x: add(x.group(0), f"P{len(m)}"), text)
    # newlines
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n", lambda _: add("\n", f"NL{len(m)}"), text)
    # glossary (longest first, whole words, case-insensitive)
    if glossary:
        for src, dst in GLOSSARY:
            pat = r"(?<![\w])" + re.escape(src) + r"(?![\w])"
            text = re.sub(pat, lambda _, d=dst: add(d, f"G{len(m)}"), text, flags=re.I)
    return text, m

def restore(text, m):
    # Google sometimes injects zero-width chars/spaces, or turns [[X]] into 【[X]].
    text = text.translate(dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None))
    lookup = {k[2:-2]: v for k, v in m.items()}
    def sub(mt):
        key = re.sub(r"\s+", "", mt.group(1))
        return lookup.get(key, mt.group(0))
    text = re.sub(r"[\[【]{1,2}\s*([A-Z]+\d+)\s*[\]】]{1,2}", sub, text)
    for token, rep in sorted(m.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(token, rep)
    return text

def clean_zh(text):
    text = text.translate(dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None))
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"\s*([，。！？；：、）】》”’])\s*", r"\1", line)
        line = re.sub(r"([（【《“‘])\s*", r"\1", line)
        line = re.sub(r"(?<=[\u4e00-\u9fff])\s+", "", line)
        line = re.sub(r"\s+(?=[\u4e00-\u9fff])", "", line)
        lines.append(line)
    return "\n".join(lines).strip()

def post_terms(src, zh):
    """Fix terminology Google routinely gets wrong when glossary masking is skipped."""
    def has(*words):
        return any(re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", src, re.I)
                   for w in words)
    if has("Caps", "CAPS", "Bottlecap", "Bottlecaps"):
        zh = zh.replace("帽子", "瓶盖").replace("上限", "瓶盖").replace("大写", "瓶盖")
    if has("Stimpak", "Stimpaks"):
        zh = zh.replace("针剂", "治疗针").replace("刺激包", "治疗针").replace("兴奋剂", "治疗针")
    if has("RadAway"):
        zh = zh.replace("辐射药", "消辐宁").replace("消辐灵", "消辐宁")
    if has("Rad-X"):
        zh = zh.replace("抗辐射", "抗辐宁")
    if has("Overseer"):
        zh = zh.replace("监工", "监督者").replace("工头", "监督者")
    if has("Ghoul", "Ghouls"):
        zh = zh.replace("食尸鬼", "尸鬼")
    if has("Deathclaw", "Deathclaws"):
        zh = zh.replace("死亡爪", "死爪")
    if has("Nuka-Cola"):
        zh = zh.replace("努卡可乐", "核子可乐").replace("努卡·可乐", "核子可乐")
    if has("Raider", "Raiders"):
        zh = zh.replace("袭击者", "掠夺者")
    return zh

def translate_single(s):
    for glossary in (True, False):
        mt, mp = protect(s, glossary=glossary)
        for attempt in range(3):
            try:
                o = clean_zh(restore(translate_batch([mt])[0], mp))
                if o and "[[" not in o and "]]" not in o:
                    return post_terms(s, o)
            except Exception:
                pass
            time.sleep(1.5 * (attempt + 1))
    return None

def translate_batch(texts):
    data = urllib.parse.urlencode([("q", t) for t in texts]).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode("utf-8")
    res = json.loads(raw)
    if not isinstance(res, list):
        raise ValueError(f"unexpected response: {raw[:200]}")
    # API sometimes wraps single result as [["x"]] etc.
    out = []
    for item in res:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, list) and item and isinstance(item[0], str):
            # could be ["translated", "source", ...]
            out.append(item[0])
        else:
            out.append("")
    if len(out) != len(texts):
        raise ValueError(f"batch size mismatch {len(out)} != {len(texts)}: {raw[:200]}")
    return out

def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, CACHE)

def main():
    with open(ORIGINAL, encoding="utf-8") as f:
        d = json.load(f)
    en = [t["Languages"][0] for t in d["mTerms"]]
    todo = sorted({s for s in en if s and s.strip()})
    todo = [s for s in todo if not re.fullmatch(r"[\s\d\W_]*", s, re.S)
            and re.search(r"[A-Za-z]", s)]
    cache = load_cache()
    pending = [s for s in todo if s not in cache]
    print(f"unique={len(todo)} cached={len(cache)} pending={len(pending)}", flush=True)
    t0 = time.time(); done = 0
    token_re = re.compile(r"[\[【]{1,2}[A-Z]+\d+[\]】]{1,2}")
    for i in range(0, len(pending), BATCH):
        chunk = pending[i:i+BATCH]
        masked, maps = [], []
        for s in chunk:
            mt, mp = protect(s)
            masked.append(mt); maps.append(mp)
        outs = None
        for attempt in range(3):
            try:
                outs = translate_batch(masked)
                break
            except Exception as e:
                print(f"batch retry {attempt+1} at {i}: {type(e).__name__}: {e}", flush=True)
                time.sleep(2 * (attempt + 1))
        bad = []
        if outs is not None:
            for s, raw, mp in zip(chunk, outs, maps):
                o = clean_zh(restore(raw, mp))
                if o and "[[" not in o and "]]" not in o and not token_re.search(o):
                    cache[s] = post_terms(s, o)
                else:
                    bad.append(s)
        else:
            bad = list(chunk)
        for s in bad:
            zh = translate_single(s)
            if zh:
                cache[s] = zh
            else:
                print("UNTRANSLATED", repr(s[:160]), flush=True)
        done += len(chunk)
        save_cache(cache)
        if done % 200 < BATCH or done == len(pending):
            elapsed = time.time() - t0
            rate = done / max(elapsed, 1e-9)
            eta = (len(pending) - done) / max(rate, 1e-9)
            print(f"progress {done}/{len(pending)} {rate:.1f}/s eta {eta/60:.1f}min "
                  f"cached={len(cache)}", flush=True)
        time.sleep(0.1 + random.random() * 0.15)
    save_cache(cache)
    print(f"DONE translated={len(cache)} in {(time.time()-t0)/60:.1f}min", flush=True)

if __name__ == "__main__":
    main()
