"""Start the relay server with the system Python."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE_FILE = ROOT / ".env.example"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE_FILE.exists():
        raise FileNotFoundError(f"Missing env template: {ENV_EXAMPLE_FILE}")
    ENV_FILE.write_text(ENV_EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[start] created {ENV_FILE.name} from template, please update AUTH_TOKEN if needed")


def resolve_runtime_config() -> tuple[str, int]:
    env_values = read_env_file(ENV_FILE)
    host = env_values.get("HOST", "0.0.0.0")
    port = int(env_values.get("PORT", "8765"))
    return host, port


def can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def main() -> None:
    ensure_env_file()
    host, port = resolve_runtime_config()

    if not can_bind(host, port):
        print(f"[start] cannot start relay server because {host}:{port} is already in use")
        print("[start] stop the existing process or change PORT in .env and try again")
        raise SystemExit(1)

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "homecopy.server.app:app",
        "--host",
        host,
        "--port",
        str(port),
        "--no-use-colors",
    ]
    subprocess.run(command, check=True, cwd=ROOT, env=env)


if __name__ == "__main__":
    main()
