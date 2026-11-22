#!/usr/bin/env python3
"""Build the Win32 installer distribution zip."""
import argparse, os, shutil, subprocess, sys, zipfile

W = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(W)
PROJ = os.path.join(W, "fs_installer")
DIST = os.path.join(W, "dist")
PAYLOAD = os.path.join(ROOT, "patch_data.unity3d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.1.0")
    args = ap.parse_args()
    v = args.version

    print("cargo build --release", flush=True)
    subprocess.run(["cargo", "build", "--release"], cwd=PROJ, check=True)
    exe = os.path.join(PROJ, "target", "release", "fs_installer.exe")
    if not os.path.exists(exe):
        raise SystemExit("missing " + exe)
    if not os.path.exists(PAYLOAD):
        raise SystemExit("missing " + PAYLOAD)

    stage = os.path.join(DIST, f"FalloutShelter_Installer_Win32_v{v}")
    if os.path.exists(stage):
        shutil.rmtree(stage)
    os.makedirs(os.path.join(stage, "payload"), exist_ok=True)
    shutil.copyfile(exe, os.path.join(stage, "fs_installer.exe"))
    shutil.copyfile(PAYLOAD, os.path.join(stage, "payload", "data.unity3d"))
    shutil.copyfile(os.path.join(ROOT, "翻译清单.csv"), os.path.join(stage, "翻译清单.csv"))
    shutil.copyfile(os.path.join(ROOT, "README.txt"), os.path.join(stage, "汉化补丁说明.txt"))
    shutil.copyfile(os.path.join(W, "README.md"), os.path.join(stage, "安装器说明.md"))

    zip_path = os.path.join(DIST, f"FalloutShelter_Installer_Win32_v{v}.zip")
    print("zipping", zip_path, flush=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for base, _, files in os.walk(stage):
            for f in files:
                p = os.path.join(base, f)
                z.write(p, os.path.relpath(p, stage))
    print(f"OK {zip_path} {os.path.getsize(zip_path)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
