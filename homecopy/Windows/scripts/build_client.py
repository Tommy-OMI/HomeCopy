"""Build a portable Windows GUI executable for the HomeCopy client."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "HomeCopyClient.spec"
DEPLOY_DIR = Path("D:/HomeCopyClient")


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
        "--collect-submodules",
        "homecopy",
        "homecopy/client/launcher_main.py",
    ]
    if sys.platform != "win32":
        command.extend(["--collect-all", "pynput"])
    run(command)

    if sys.platform == "win32":
        if DEPLOY_DIR.exists():
            shutil.rmtree(DEPLOY_DIR)
        shutil.copytree(DIST_DIR / "HomeCopyClient", DEPLOY_DIR, dirs_exist_ok=True)
        print(f"[build] copied portable client to {DEPLOY_DIR}")

    print(f"[build] output ready at {DIST_DIR / 'HomeCopyClient'}")


if __name__ == "__main__":
    main()
