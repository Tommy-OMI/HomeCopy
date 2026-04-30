"""Startup orchestration for the unified HomeCopy app."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from homecopy.client.config import ClientConfig
from homecopy.client.discovery import discover_server
from homecopy.server.config import get_settings


DISCOVERY_WAIT_SECONDS = 3.0
SERVER_HEALTH_WAIT_SECONDS = 8.0
SERVER_HEALTH_POLL_INTERVAL = 0.4


def local_server_url() -> str:
    settings = get_settings()
    return f"ws://127.0.0.1:{settings.port}/ws"


def healthcheck_url() -> str:
    settings = get_settings()
    return f"http://127.0.0.1:{settings.port}/healthz"


def is_server_healthy(url: str | None = None, timeout: float = 1.0) -> bool:
    target = url or healthcheck_url()
    try:
        with urllib.request.urlopen(target, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def wait_for_server_health(timeout: float = SERVER_HEALTH_WAIT_SECONDS) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_server_healthy():
            return True
        time.sleep(SERVER_HEALTH_POLL_INTERVAL)
    return False


def spawn_embedded_server(root: Path) -> subprocess.Popen[bytes]:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "server.log"
    log_handle = open(log_file, "ab")

    if getattr(sys, "frozen", False):
        command = [sys.executable, "--server-mode"]
    else:
        command = [sys.executable, "-m", "homecopy.client.launcher_main", "--server-mode"]

    creationflags = 0
    startupinfo = None
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    return subprocess.Popen(
        command,
        cwd=root,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
        startupinfo=startupinfo,
        close_fds=True,
    )


def resolve_runtime_server_url(root: Path) -> str:
    discovery_result = asyncio.run(discover_server(timeout=DISCOVERY_WAIT_SECONDS))
    if discovery_result is not None:
        return discovery_result.server_url

    if is_server_healthy():
        return local_server_url()

    spawn_embedded_server(root)
    if wait_for_server_health():
        return local_server_url()

    raise RuntimeError("Unable to discover or start a HomeCopy server.")


def prepare_client_config(config_path: Path, root: Path) -> ClientConfig:
    config = ClientConfig.load(config_path)
    if config.auto_start_server_if_missing:
        server_url = resolve_runtime_server_url(root)
    else:
        server_url = config.server_url
    if config.server_url != server_url:
        config = config.model_copy(update={"server_url": server_url})
        config.save(config_path)
    return config
