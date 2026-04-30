"""One-click dependency installer using the system Python."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements.txt"


def run(command: list[str]) -> None:
    print(f"[install] {' '.join(command)}")
    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    if not REQUIREMENTS.exists():
        raise FileNotFoundError(f"requirements.txt not found: {REQUIREMENTS}")

    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    print("[install] done")


if __name__ == "__main__":
    main()
