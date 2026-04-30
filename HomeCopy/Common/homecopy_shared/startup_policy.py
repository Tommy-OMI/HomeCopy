"""Unified client startup policy shared by desktop entrypoints."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlsplit, urlunsplit

from homecopy.client.config import ClientConfig
from homecopy.client.discovery import discover_server
from homecopy.server.config import get_settings


DISCOVERY_WAIT_SECONDS = 3.0
DISCOVERY_RECHECK_SECONDS = 1.5
REMOTE_SERVER_HEALTH_WAIT_SECONDS = 3.0
SERVER_HEALTH_WAIT_SECONDS = 8.0
SERVER_HEALTH_POLL_INTERVAL = 0.4
SERVER_SHUTDOWN_WAIT_SECONDS = 3.0
STARTUP_TRACE_FILE = "client-startup.log"
ConfirmStartServer = Callable[[], bool]
MissingServerAction = Literal["connect", "start_local", "cancel"]

logger = logging.getLogger(__name__)


def write_startup_trace(root: Path, message: str) -> None:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    trace_path = logs_dir / STARTUP_TRACE_FILE
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with trace_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")
    except Exception:
        logger.exception("Failed to write startup trace")


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


@dataclass(slots=True)
class MissingServerResolution:
    action: MissingServerAction
    server_url: str | None = None


ResolveMissingServer = Callable[[Path, ClientConfig], MissingServerResolution]


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


def check_server_health(url: str | None = None, timeout: float = 1.0) -> tuple[bool, str | None]:
    target = url or healthcheck_url()
    try:
        with urllib.request.urlopen(target, timeout=timeout) as response:
            return response.status == 200, None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return False, str(exc)


def is_server_healthy(url: str | None = None, timeout: float = 1.0) -> bool:
    healthy, _ = check_server_health(url=url, timeout=timeout)
    return healthy


def wait_for_server_health(
    url: str | None = None,
    timeout: float = SERVER_HEALTH_WAIT_SECONDS,
    root: Path | None = None,
) -> bool:
    deadline = time.time() + timeout
    last_error: str | None = None
    while time.time() < deadline:
        healthy, error_text = check_server_health(url=url)
        if healthy:
            return True
        last_error = error_text
        time.sleep(SERVER_HEALTH_POLL_INTERVAL)
    if root is not None and url is not None:
        if last_error:
            write_startup_trace(root, f"healthcheck timeout url={url} error={last_error}")
        else:
            write_startup_trace(root, f"healthcheck timeout url={url}")
    return False


def discover_healthy_remote_server(root: Path, timeout: float) -> str | None:
    try:
        discovery_result = asyncio.run(discover_server(timeout=timeout))
    except Exception:
        write_startup_trace(root, f"LAN discovery raised exception timeout={timeout}")
        logger.exception("LAN discovery failed during startup")
        return None

    if discovery_result is None:
        write_startup_trace(root, f"LAN discovery found no server timeout={timeout}")
        return None

    server_url = discovery_result.server_url
    write_startup_trace(root, f"LAN discovery found server {server_url} timeout={timeout}")
    if wait_for_server_health(
        url=healthcheck_url_for_server(server_url),
        timeout=REMOTE_SERVER_HEALTH_WAIT_SECONDS,
        root=root,
    ):
        write_startup_trace(root, f"LAN discovery healthcheck ok {server_url}")
        return server_url

    write_startup_trace(root, f"LAN discovery healthcheck failed {server_url}")
    logger.warning("Discovered server was not healthy: %s", server_url)
    return None


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
    config_path: Path,
    root: Path,
    config: ClientConfig,
    confirm_start_server: ConfirmStartServer | None = None,
    resolve_missing_server: ResolveMissingServer | None = None,
) -> tuple[str, EmbeddedServerController]:
    write_startup_trace(root, f"resolve_runtime_server start timeout={DISCOVERY_WAIT_SECONDS}")
    remote_server_url = discover_healthy_remote_server(root, timeout=DISCOVERY_WAIT_SECONDS)
    if remote_server_url is not None:
        write_startup_trace(root, f"selected remote server {remote_server_url}")
        return remote_server_url, EmbeddedServerController()

    if is_server_healthy():
        write_startup_trace(root, "local server is healthy before fallback")
        remote_server_url = discover_healthy_remote_server(root, timeout=DISCOVERY_RECHECK_SECONDS)
        if remote_server_url is not None:
            write_startup_trace(root, f"selected remote server after recheck {remote_server_url}")
            return remote_server_url, EmbeddedServerController()
        write_startup_trace(root, f"selected local server {local_server_url()}")
        return local_server_url(), EmbeddedServerController()

    if resolve_missing_server is not None:
        resolution = resolve_missing_server(config_path, config)
        write_startup_trace(
            root,
            f"missing server resolution action={resolution.action} server_url={resolution.server_url or ''}",
        )
        if resolution.action == "cancel":
            raise RuntimeError("HomeCopy startup was cancelled.")
        if resolution.action == "connect":
            selected_server_url = (resolution.server_url or config.server_url).strip()
            if not selected_server_url:
                raise RuntimeError("No HomeCopy server URL was provided.")
            return selected_server_url, EmbeddedServerController()
        if resolution.action == "start_local":
            write_startup_trace(root, "spawning embedded local server from setup dialog")
            server_controller = spawn_embedded_server(root)
            if wait_for_server_health(root=root):
                write_startup_trace(root, f"embedded local server became healthy {local_server_url()}")
                return local_server_url(), server_controller
            server_controller.shutdown()
            write_startup_trace(root, "embedded local server failed healthcheck after setup dialog")
            raise RuntimeError("Unable to start a local HomeCopy server.")

    if confirm_start_server is not None and not confirm_start_server():
        write_startup_trace(root, "local server startup cancelled by user")
        raise RuntimeError("Local server startup was cancelled.")

    write_startup_trace(root, "spawning embedded local server")
    server_controller = spawn_embedded_server(root)
    if wait_for_server_health(root=root):
        write_startup_trace(root, f"embedded local server became healthy {local_server_url()}")
        return local_server_url(), server_controller

    server_controller.shutdown()
    write_startup_trace(root, "embedded local server failed healthcheck")
    raise RuntimeError("Unable to discover or start a HomeCopy server.")


def prepare_client_launch(
    config_path: Path,
    root: Path,
    confirm_start_server: ConfirmStartServer | None = None,
    resolve_missing_server: ResolveMissingServer | None = None,
) -> ClientLaunchContext:
    config = ClientConfig.load(config_path)
    write_startup_trace(root, f"prepare_client_launch config_path={config_path} configured_server={config.server_url}")
    server_controller = EmbeddedServerController()

    if config.auto_start_server_if_missing:
        server_url, server_controller = resolve_runtime_server(
            config_path,
            root,
            config,
            confirm_start_server=confirm_start_server,
            resolve_missing_server=resolve_missing_server,
        )
        config = ClientConfig.load(config_path)
    else:
        server_url = config.server_url

    if config.server_url != server_url:
        config = config.model_copy(update={"server_url": server_url})
        config.save(config_path)
        write_startup_trace(root, f"updated config server_url={server_url}")
    else:
        write_startup_trace(root, f"config server_url unchanged={server_url}")

    return ClientLaunchContext(
        config_path=config_path,
        config=config,
        server_controller=server_controller,
    )
