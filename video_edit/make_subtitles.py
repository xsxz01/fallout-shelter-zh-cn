#!/usr/bin/env python3
"""Generate draft SRT/ASS from the script and edit_plan durations."""
import json, re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD = ROOT.parent / "B站视频脚本_90秒.md"

def read_lines():
    s = MD.read_text(encoding="utf-8")
    m = re.search(r"### 1\.2 纯 TTS 文本.*?```text\n(.*?)```", s, re.S)
    if not m:
        raise SystemExit("narration 1.2 not found")
    return [x.strip() for x in m.group(1).splitlines() if x.strip()]

def split_text(s, max_chars=24):
    parts = re.split(r"(?<=[，。；！？、])", s)
    out, cur = [], ""
    for p in parts:
        if not p:
            continue
        if len(cur) + len(p) <= max_chars:
            cur += p
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    # hard-wrap very long chunks
    final = []
    for x in out:
        while len(x) > max_chars:
            cut = max(x.rfind("，", 0, max_chars), x.rfind("。", 0, max_chars))
            if cut <= 8:
                cut = max_chars
            final.append(x[:cut + 1])
            x = x[cut + 1:]
        if x:
            final.append(x)
    return final

def ts(sec, ass=False):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    if ass:
        return f"{h}:{m:02d}:{s:05.2f}"
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"

def main():
    plan = json.load(open(ROOT / "edit_plan.json", encoding="utf-8"))
    lines = read_lines()
    scenes = plan["scenes"]
    if len(lines) > len(scenes) - 1:
        raise SystemExit("more narration lines than scenes")
    t = 0.0
    srt, ass = [], []
    for i, sc in enumerate(scenes):
        dur = float(sc["duration"])
        if i < len(lines):
            chunks = split_text(lines[i])
            total = sum(len(x) for x in chunks) or 1
            ct = t
            for ch in chunks:
                d = dur * len(ch) / total
                srt.append((ct, ct + d, ch))
                ass.append((ct, ct + d, ch))
                ct += d
        t += dur
    os.makedirs("subtitles", exist_ok=True)
    with open("subtitles/draft.srt", "w", encoding="utf-8") as f:
        for n, (a, b, text) in enumerate(srt, 1):
            f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{text}\n\n")
    with open("subtitles/draft.ass", "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write("Style: Default,Microsoft YaHei UI,42,&H00F0FFF0,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,80,80,70,1\n\n")
        f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for a, b, text in ass:
            text = text.replace("\n", r"\N")
            f.write(f"Dialogue: 0,{ts(a, True)},{ts(b, True)},Default,,0,0,0,,{{\\fad(150,150)}}{text}\n")
    print(f"subtitles: {len(srt)} entries")
    print("duration:", t, "sec")

if __name__ == "__main__":
    main()
