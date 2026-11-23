#!/usr/bin/env python3
"""Validate translations against source terms and print quality signals."""
import json, re, sys, collections, os
from project_paths import CACHE, ORIGINAL
d = json.load(open(ORIGINAL, encoding="utf-8"))
cache = json.load(open(CACHE, encoding="utf-8"))
terms = d["mTerms"]
en = [t["Languages"][0] for t in terms]
uniq = sorted({s for s in en if s and s.strip() and re.search(r"[A-Za-z]", s)})
missing = [s for s in uniq if s not in cache]
print(f"unique={len(uniq)} translated={len(uniq)-len(missing)} missing={len(missing)}")

def toks(s):
    return {
        "braces": sorted(re.findall(r"\{[^{}]*\}", s)),
        "brackets": sorted(re.findall(r"\[[^\[\]]*\]", s)),
        "newlines": s.count("\n"),
    }

bad_tokens = []; empty = []; same = []; too_long = []
for s in uniq:
    z = cache.get(s)
    if not z:
        continue
    if not z.strip():
        empty.append(s); continue
    a, b = toks(s), toks(z)
    if a["braces"] != b["braces"] or a["brackets"] != b["brackets"] or a["newlines"] != b["newlines"]:
        bad_tokens.append((s, z, a, b))
    if z.strip() == s.strip():
        same.append(s)
    if len(z) > max(16, len(s) * 2.5):
        too_long.append((len(s), len(z), s, z))

print("bad_token", len(bad_tokens), "empty", len(empty), "identical", len(same), "too_long", len(too_long))
for s, z, a, b in bad_tokens[:10]:
    print("TOK", repr(s[:100]), "=>", repr(z[:100]), a, b)
for s in same[:10]:
    print("SAME", repr(s[:100]))
for a, b, s, z in too_long[:10]:
    print("LONG", a, b, repr(s[:80]), "=>", repr(z[:80]))
print("missing sample:")
for s in missing[:30]:
    print("  ", repr(s[:150]))

# non-Chinese output check (contains latin words but no CJK)
no_cjk = [s for s in uniq if s in cache and not re.search(r"[\u4e00-\u9fff]", cache[s])]
print("no_cjk", len(no_cjk))
for s in no_cjk[:20]:
    print("  ", repr(s[:100]), "=>", repr(cache[s][:100]))
