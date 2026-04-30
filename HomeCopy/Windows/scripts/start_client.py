"""Resolve a client config and launch the HomeCopy GUI client."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from homecopy.client.launcher import resolve_config_path

def main() -> None:
    try:
        config_arg = sys.argv[1] if sys.argv[1:] else None
        config_path = resolve_config_path(config_arg)
    except FileNotFoundError as exc:
        print(f"[start-client] {exc}")
        raise SystemExit(1)

    if not config_path.exists():
        print(f"[start-client] config file not found: {config_path}")
        raise SystemExit(1)

    command = [
        sys.executable,
        "-m",
        "homecopy.client.launcher_main",
        "--config",
        str(config_path),
    ]
    subprocess.run(command, check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
