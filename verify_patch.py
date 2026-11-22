#!/usr/bin/env python3
"""Read back the generated bundle and verify the localization and fonts."""
import json, os, re, sys
import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.helpers.TypeTreeHelper import read_value, TypeTreeConfig

W = os.path.dirname(os.path.abspath(__file__))
GAMEDIR = r"D:/Program Files (x86)/Steam/steamapps/common/Fallout Shelter"
PATCH = os.path.join(W, "patch_data.unity3d")
ov = json.load(open(os.path.join(W, "overrides.json"), encoding="utf-8"))

gen = TypeTreeGenerator("6000.0.58f2")
gen.load_local_game(GAMEDIR)
env = UnityPy.load(PATCH)
env.typetree_generator = gen
x = env.file.files["resources.assets"]
o = x.objects[20953]
node = o.generate_monobehaviour_node()

def fix(n):
    if n.m_Type == "UInt8" and n.m_Name == "m_Enabled":
        n.m_MetaFlag = 0x4000
    arr = [c for c in n.m_Children if c.m_Type == "Array" and c.m_Name == "Array"]
    if arr and arr[0].m_Children[1].m_Type != "char":
        n.m_Type = "vector"
    for c in n.m_Children:
        fix(c)

fix(node)
o.reset()
d = read_value(node, o.reader, TypeTreeConfig(True, x, False))
terms = {t["Term"]: t for t in d["mTerms"]}
print("terms", len(terms))
print("language0", d["mLanguages"][0])
zh = sum(1 for t in terms.values() if re.search(r"[\u4e00-\u9fff]", t["Languages"][0]))
print("terms_with_cjk", zh)
bad = 0
for k, v in ov.items():
    if k not in terms:
        print("MISSING TERM KEY", k); bad += 1
    elif terms[k]["Languages"][0] != v:
        print("OVERRIDE MISMATCH", k, repr(terms[k]["Languages"][0]), "!=", repr(v)); bad += 1
print("override_mismatches", bad)
fonts = []
for obj in env.objects:
    if obj.type.name == "Font":
        f = obj.read()
        fonts.append((f.m_Name, len(f.m_FontData), bytes(f.m_FontData[:4])))
print("fonts", fonts)
for name, n, sig in fonts:
    assert sig == b"\x00\x01\x00\x00", (name, sig)
    assert n > 1_000_000, (name, n)
# token sanity across all translations
tok = re.compile(r"[\[【]{1,2}[A-Z]+\d+[\]】]{1,2}")
bad_tok = [k for k, t in terms.items() if tok.search(t["Languages"][0]) or "[[" in t["Languages"][0]]
print("leftover_tokens", len(bad_tok), bad_tok[:5])
print("empty_zh", sum(1 for t in terms.values() if not t["Languages"][0].strip()))
print("OK" if not bad and not bad_tok else "CHECK FAILED")
