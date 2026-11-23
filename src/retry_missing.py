#!/usr/bin/env python3
"""Retry terms missing from the cache and drop obviously corrupted entries."""
import json, os, re, time
import translate as T
from project_paths import ORIGINAL

d = json.load(open(ORIGINAL, encoding="utf-8"))
cache = T.load_cache()
en = [t["Languages"][0] for t in d["mTerms"]]
todo = sorted({s for s in en if s and s.strip() and re.search(r"[A-Za-z]", s)})

token_re = re.compile(r"[\[【]{1,2}[A-Z]+\d+[\]】]{1,2}")
dropped = []
for k in list(cache):
    v = cache[k]
    if not v.strip() or token_re.search(v) or "[[" in v or "]]" in v:
        dropped.append(k)
        del cache[k]
print("dropped corrupt", len(dropped))

missing = [s for s in todo if s not in cache]
print("missing", len(missing))
token_re = re.compile(r"[\[【]{1,2}[A-Z]+\d+[\]】]{1,2}")
i = 0
while i < len(missing):
    chunk = missing[i:i+20]
    masked, maps = [], []
    for s in chunk:
        mt, mp = T.protect(s, glossary=False)
        masked.append(mt); maps.append(mp)
    try:
        outs = T.translate_batch(masked)
    except Exception as e:
        print("batch failed", e)
        outs = None
    if outs:
        for s, out, mp in zip(chunk, outs, maps):
            zh = T.clean_zh(T.restore(out, mp))
            if zh and "[[" not in zh and "]]" not in zh and not token_re.search(zh):
                cache[s] = T.post_terms(s, zh)
            else:
                zh = T.translate_single(s)
                if zh:
                    cache[s] = zh
    else:
        for s in chunk:
            zh = T.translate_single(s)
            if zh:
                cache[s] = zh
    i += len(chunk)
    T.save_cache(cache)
    print(i, "/", len(missing), "cached", len(cache), flush=True)
T.save_cache(cache)
print("done cached", len(cache), "remaining", len([s for s in todo if s not in cache]))
