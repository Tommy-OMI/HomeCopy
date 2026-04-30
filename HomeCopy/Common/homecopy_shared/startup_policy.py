"""Unified client startup policy shared by desktop entrypoints."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

from homecopy.client.config import ClientConfig
from homecopy.client.discovery import discover_server
from homecopy.server.config import get_settings


DISCOVERY_WAIT_SECONDS = 3.0
SERVER_HEALTH_WAIT_SECONDS = 8.0
SERVER_HEALTH_POLL_INTERVAL = 0.4
SERVER_SHUTDOWN_WAIT_SECONDS = 3.0
ConfirmStartServer = Callable[[], bool]


@dataclass(slots=True)
class EmbeddedServerController:
    process: subprocess.Popen[bytes] | None = None
    started_by_app: bool = False
    _closed: bool = False

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True

        if not self.started_by_app or self.process is None:
            return

        process = self.process
        self.process = None

        if process.poll() is not None:
            return

        try:
            process.terminate()
            process.wait(timeout=SERVER_SHUTDOWN_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=SERVER_SHUTDOWN_WAIT_SECONDS)
        except ProcessLookupError:
            return


@dataclass(slots=True)
class ClientLaunchContext:
    config_path: Path
    config: ClientConfig
    server_controller: EmbeddedServerController


def local_server_url() -> str:
    settings = get_settings()
    return f"ws://127.0.0.1:{settings.port}/ws"


def healthcheck_url() -> str:
    settings = get_settings()
    return f"http://127.0.0.1:{settings.port}/healthz"


def healthcheck_url_for_server(server_url: str) -> str:
    parts = urlsplit(server_url)
    scheme = "https" if parts.scheme == "wss" else "http"
    return urlunsplit((scheme, parts.netloc, "/healthz", "", ""))


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


def spawn_embedded_server(root: Path) -> EmbeddedServerController:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "server.log"

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

    log_handle = open(log_file, "ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            startupinfo=startupinfo,
            close_fds=True,
        )
    finally:
        log_handle.close()

    return EmbeddedServerController(process=process, started_by_app=True)


def resolve_runtime_server(
    root: Path,
    confirm_start_server: ConfirmStartServer | None = None,
) -> tuple[str, EmbeddedServerController]:
    try:
        discovery_result = asyncio.run(discover_server(timeout=DISCOVERY_WAIT_SECONDS))
    except Exception:
        discovery_result = None

    if discovery_result is not None:
        server_url = discovery_result.server_url
        if is_server_healthy(healthcheck_url_for_server(server_url)):
            return server_url, EmbeddedServerController()

    if is_server_healthy():
        return local_server_url(), EmbeddedServerController()

    if confirm_start_server is not None and not confirm_start_server():
        raise RuntimeError("Local server startup was cancelled.")

    server_controller = spawn_embedded_server(root)
    if wait_for_server_health():
        return local_server_url(), server_controller

    server_controller.shutdown()
    raise RuntimeError("Unable to discover or start a HomeCopy server.")


def prepare_client_launch(
    config_path: Path,
    root: Path,
    confirm_start_server: ConfirmStartServer | None = None,
) -> ClientLaunchContext:
    config = ClientConfig.load(config_path)
    server_controller = EmbeddedServerController()

    if config.auto_start_server_if_missing:
        server_url, server_controller = resolve_runtime_server(
            root,
            confirm_start_server=confirm_start_server,
        )
    else:
        server_url = config.server_url

    if config.server_url != server_url:
        config = config.model_copy(update={"server_url": server_url})
        config.save(config_path)

    return ClientLaunchContext(
        config_path=config_path,
        config=config,
        server_controller=server_controller,
    )
