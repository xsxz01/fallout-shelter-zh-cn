#!/usr/bin/env python3
"""Build a versioned release package and optionally publish it with gh."""
import argparse, hashlib, os, shutil, subprocess, sys, zipfile

from project_paths import DIST, PATCH_DATA, PATCH_DIR, LIST_CSV, SRC, VERSION_FILE

FILES = ["data.unity3d", "安装汉化.bat", "还原英文.bat", "README.txt", "翻译清单.csv"]


def read_version():
    try:
        return open(VERSION_FILE, encoding="utf-8").read().strip()
    except OSError:
        return "1.0.0"


def bump(v):
    parts = v.split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        parts[-1] = "1"
    return ".".join(parts[:3])


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=read_version())
    ap.add_argument("--notes", default="")
    ap.add_argument("--no-release", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--no-bump", action="store_true")
    args = ap.parse_args()
    v = args.version

    print("[0/4] 导出翻译清单 ...", flush=True)
    subprocess.run([sys.executable, str(SRC / "export_list.py")], cwd=SRC, check=True)

    if not args.skip_build:
        print("[1/4] 构建 data.unity3d ...", flush=True)
        subprocess.run([sys.executable, str(SRC / "build_patch.py")], cwd=SRC, check=True)
        shutil.copyfile(PATCH_DATA, os.path.join(PATCH_DIR, "data.unity3d"))
        shutil.copyfile(LIST_CSV, os.path.join(PATCH_DIR, "翻译清单.csv"))

    os.makedirs(DIST, exist_ok=True)
    zip_path = os.path.join(DIST, f"FalloutShelter_2.7.0_zh-CN_v{v}.zip")
    print(f"[2/4] 打包 {zip_path}", flush=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for name in FILES:
            src = os.path.join(PATCH_DIR, name)
            if not os.path.exists(src):
                raise SystemExit(f"缺少文件: {src}")
            z.write(src, arcname=name)
    size = os.path.getsize(zip_path)
    digest = md5(zip_path)
    print(f"      {size/1024/1024:.1f} MB  MD5 {digest}", flush=True)
    print(f"      data.unity3d MD5 {md5(os.path.join(PATCH_DIR, 'data.unity3d'))}", flush=True)

    if not args.no_release:
        print("[3/4] 上传 GitHub Release ...", flush=True)
        notes = args.notes.strip() or (
            f"Fallout Shelter 2.7.0 简体中文汉化补丁 v{v}\n\n"
            f"- 当前汉化包版本：v{v}\n"
            f"- 文本条目：14,073 条\n"
            f"- 字体：SimHei 精简子集\n"
            f"- data.unity3d MD5：{md5(os.path.join(PATCH_DIR, 'data.unity3d'))}\n\n"
            "安装：解压后把 data.unity3d 覆盖到 FalloutShelter_Data，"
            "或运行压缩包内的“安装汉化.bat”。"
        )
        cmd = ["gh", "release", "create", f"v{v}", zip_path,
               "--title", f"Fallout Shelter 2.7.0 简体中文汉化 v{v}",
               "--notes", notes, "--latest"]
        subprocess.run(cmd, cwd=SRC, check=True)
        print(f"[4/4] 已发布 v{v}", flush=True)
        if not args.no_bump:
            nv = bump(v)
            open(VERSION_FILE, "w", encoding="utf-8").write(nv + "\n")
            print(f"下次版本号：{nv}", flush=True)
    else:
        print("[3/4] 跳过 GitHub 发布（--no-release）", flush=True)
        print("[4/4] 完成", flush=True)


if __name__ == "__main__":
    main()
