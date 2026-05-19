"""Build a portable Windows GUI executable for the HomeCopy client."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COMMON_ROOT = ROOT.parent / "Common"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "HomeCopyClient.spec"


def run(command: list[str]) -> None:
    print(f"[build] {' '.join(command)}")
    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0,<7.0"])

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if SPEC_FILE.exists():
        SPEC_FILE.unlink()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "HomeCopyClient",
        "--paths",
        str(ROOT),
        "--paths",
        str(COMMON_ROOT),
        "--collect-submodules",
        "homecopy",
        "--collect-submodules",
        "homecopy_shared",
        "homecopy/client/launcher_main.py",
    ]
    if sys.platform != "win32":
        command.extend(["--collect-all", "pynput"])
    run(command)

    deploy_dir_raw = os.environ.get("HOMECOPY_DEPLOY_DIR", "").strip()
    if sys.platform == "win32" and deploy_dir_raw:
        deploy_dir = Path(deploy_dir_raw)
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir)
        shutil.copytree(DIST_DIR / "HomeCopyClient", deploy_dir, dirs_exist_ok=True)
        print(f"[build] copied portable client to {deploy_dir}")

    print(f"[build] output ready at {DIST_DIR / 'HomeCopyClient'}")


if __name__ == "__main__":
    main()
