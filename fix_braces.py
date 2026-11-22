#!/usr/bin/env python3
"""Translate the highlighted text inside {...} markup."""
import json, re
from pathlib import Path

W = Path(__file__).parent
m = json.load(open(W/'brace_map.json', encoding='utf-8'))

def fix(s):
    def rep(mt):
        inner = mt.group(1)
        if not re.search(r'[A-Za-z]', inner):
            return mt.group(0)
        key = inner.strip().upper()
        if key in m:
            return '{' + m[key] + '}'
        return mt.group(0)
    return re.sub(r'\{([^{}]*)\}', rep, s)

for name in ['translations_cache.json', 'overrides.json']:
    p = W/name
    data = json.load(open(p, encoding='utf-8'))
    changed = 0
    for k, v in list(data.items()):
        nv = fix(v)
        if nv != v:
            data[k] = nv
            changed += 1
    json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    print(name, 'changed', changed)

# report leftovers
left = set()
for name in ['translations_cache.json', 'overrides.json']:
    for v in json.load(open(W/name, encoding='utf-8')).values():
        for mt in re.finditer(r'\{([^{}]*)\}', v):
            if re.search(r'[A-Za-z]', mt.group(1)) and mt.group(1).strip().upper() not in m:
                left.add(mt.group(1))
print('unmapped', sorted(left))
