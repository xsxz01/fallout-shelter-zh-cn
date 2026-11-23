#!/usr/bin/env python3
"""Assemble the Bilibili draft from video_raw/ using edit_plan.json."""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FFMPEG = os.environ.get("FFMPEG", r"D:\\ffmpeg.exe")


def run(cmd):
    print(" ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-subs", action="store_true")
    ap.add_argument("--preview", action="store_true", help="1280x720 preview")
    ap.add_argument("--output", default="output/draft_v1.mp4")
    ap.add_argument("--plan", default="edit_plan.json")
    ap.add_argument("--raw", default="raw")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = ROOT / plan_path
    plan = json.load(open(plan_path, encoding="utf-8"))
    scenes = plan["scenes"]
    raw = Path(args.raw)
    if not raw.is_absolute():
        raw = ROOT / raw
    generated = ROOT / "generated"
    def resolve_file(name):
        for base in (raw, generated):
            p = base / name
            if p.exists():
                return p
        return None
    def parts_of(sc):
        if "segments" in sc:
            return sc["segments"]
        return [{"file": sc["file"], "start": sc.get("start", 0.0), "duration": sc["duration"]}]
    missing = []
    for sc in scenes:
        for pt in parts_of(sc):
            if resolve_file(pt["file"]) is None:
                missing.append(pt["file"])
    if missing:
        print("缺少以下素材，请放到 video_edit/raw/：")
        for m in dict.fromkeys(missing):
            print("  -", m)
        sys.exit(2)

    (ROOT / "temp").mkdir(exist_ok=True)
    (ROOT / "output").mkdir(exist_ok=True)
    normalized = []
    for sc in scenes:
        sid = sc["id"]
        parts = parts_of(sc)
        part_files = []
        for j, pt in enumerate(parts):
            src = resolve_file(pt["file"])
            start = float(pt.get("start", 0.0))
            dur = float(pt.get("duration", sc["duration"]))
            out = ROOT / "temp" / f"{sid}_p{j}.mp4"
            vf = (f"scale={plan['width']}:{plan['height']}:force_original_aspect_ratio=increase,"
                  f"crop={plan['width']}:{plan['height']},fps={plan['fps']},setsar=1,"
                  f"tpad=stop_mode=clone:stop_duration=5")
            blurs = sc.get("blur", [])
            if blurs:
                x, y, w, h = blurs[0]
                fc = f"[0:v]crop={w}:{h}:{x}:{y},boxblur=20:20[b];[0:v][b]overlay={x}:{y},{vf}[v]"
                cmd = [FFMPEG, "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
                       "-filter_complex", fc, "-map", "[v]"]
            else:
                cmd = [FFMPEG, "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
                       "-vf", vf]
            cmd += ["-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
            run(cmd)
            part_files.append(out)
        base = ROOT / "temp" / f"{sid}_base.mp4"
        if len(part_files) == 1:
            os.replace(part_files[0], base)
        else:
            lf = ROOT / "temp" / f"{sid}_list.txt"
            with open(lf, "w", encoding="utf-8") as f:
                for pth in part_files:
                    f.write(f"file '{pth.as_posix()}'\n")
            run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lf),
                 "-c", "copy", str(base)])
        overlay = ROOT / "overlays" / f"{sid}.png"
        scene_out = ROOT / "temp" / f"{sid}.mp4"
        if overlay.exists():
            run([FFMPEG, "-y", "-i", str(base), "-i", str(overlay),
                 "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
                 "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "18", "-pix_fmt", "yuv420p", str(scene_out)])
        else:
            os.replace(base, scene_out)
        normalized.append(scene_out)
    list_file = ROOT / "temp" / "list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in normalized:
            f.write(f"file '{p.as_posix()}'\n")
    concat = ROOT / "temp" / "video.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", str(concat)])

    total = sum(float(s["duration"]) for s in scenes)
    narration = ROOT / "raw" / "narration.wav"
    bgm = ROOT / "raw" / "bgm.mp3"
    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    inputs = [FFMPEG, "-y", "-i", str(concat)]
    if narration.exists():
        inputs += ["-i", str(narration)]
    if narration.exists() and bgm.exists():
        inputs += ["-stream_loop", "-1", "-i", str(bgm)]

    fc = []
    maps = []
    if narration.exists():
        if bgm.exists():
            fc.append("[2:a]volume=0.16[bg]")
            fc.append("[1:a]volume=1.0,asplit=2[voice][side]")
            fc.append("[bg][side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck]")
            fc.append("[voice][duck]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        else:
            fc.append("[1:a]volume=1.0[aout]")
        maps += ["-map", "0:v", "-map", "[aout]"]
    else:
        maps += ["-map", "0:v"]

    if not args.no_subs and (ROOT / "subtitles" / "draft.ass").exists():
        fc.append("[0:v]ass=subtitles/draft.ass[vout]")
        maps = ["-map", "[vout]"] + (["-map", "[aout]"] if narration.exists() else [])
    else:
        maps = ["-map", "0:v"] + (["-map", "[aout]"] if narration.exists() else [])

    cmd = inputs
    if fc:
        cmd += ["-filter_complex", ";".join(fc)]
    cmd += maps + ["-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium",
                   "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                   "-movflags", "+faststart", str(out_path)]
    if args.preview:
        cmd += []
    run(cmd)
    print("OK:", out_path)


if __name__ == "__main__":
    main()
