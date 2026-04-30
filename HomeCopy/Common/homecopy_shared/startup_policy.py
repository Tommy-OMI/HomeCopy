"""Unified client startup policy shared by desktop entrypoints."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import socket
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
SERVER_PID_FILE = "managed_server.pid"
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
    pid: int | None = None
    started_by_app: bool = False
    root: Path | None = None
    _closed: bool = False

    def is_running(self) -> bool:
        if self.process is not None:
            if self.process.poll() is None:
                return True
            self.process = None
        return self.pid is not None and is_pid_running(self.pid)

    def start(self, root: Path) -> None:
        controller = spawn_embedded_server(root)
        self.process = controller.process
        self.pid = controller.pid
        self.started_by_app = controller.started_by_app
        self.root = controller.root
        self._closed = False

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True

        if not self.started_by_app:
            return

        process = self.process
        pid = self.pid or (process.pid if process is not None else None)
        self.process = None
        self.pid = None

        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=SERVER_SHUTDOWN_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=SERVER_SHUTDOWN_WAIT_SECONDS)
            except ProcessLookupError:
                pass
        elif pid is not None:
            terminate_pid(pid)

        if self.root is not None:
            clear_managed_server_pid(self.root)


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


def local_server_display_address() -> str:
    settings = get_settings()
    return f"{resolve_preferred_local_host()}:{settings.port}"


def healthcheck_url() -> str:
    settings = get_settings()
    return f"http://127.0.0.1:{settings.port}/healthz"


def healthcheck_url_for_server(server_url: str) -> str:
    parts = urlsplit(server_url)
    scheme = "https" if parts.scheme == "wss" else "http"
    return urlunsplit((scheme, parts.netloc, "/healthz", "", ""))


def is_local_server_url(server_url: str) -> bool:
    parts = urlsplit(server_url)
    hostname = (parts.hostname or "").lower()
    return hostname in local_host_identifiers()


def local_host_identifiers() -> set[str]:
    identifiers = {"127.0.0.1", "localhost"}

    try:
        hostname = socket.gethostname().strip().lower()
        if hostname:
            identifiers.add(hostname)
    except Exception:
        pass

    try:
        canonical, aliases, addresses = socket.gethostbyname_ex(socket.gethostname())
        if canonical:
            identifiers.add(canonical.strip().lower())
        identifiers.update(alias.strip().lower() for alias in aliases if alias.strip())
        identifiers.update(address.strip().lower() for address in addresses if address.strip())
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            host = sock.getsockname()[0].strip().lower()
            if host:
                identifiers.add(host)
    except OSError:
        pass

    return identifiers


def resolve_preferred_local_host() -> str:
    for candidate in sorted(local_host_identifiers()):
        if candidate not in {"127.0.0.1", "localhost"} and "." in candidate:
            return candidate
    return "127.0.0.1"


def managed_server_pid_path(root: Path) -> Path:
    return root / "logs" / SERVER_PID_FILE


def write_managed_server_pid(root: Path, pid: int) -> None:
    path = managed_server_pid_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid), encoding="utf-8")


def clear_managed_server_pid(root: Path) -> None:
    path = managed_server_pid_path(root)
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def read_managed_server_pid(root: Path) -> int | None:
    path = managed_server_pid_path(root)
    if not path.exists():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        clear_managed_server_pid(root)
        return None
    if is_pid_running(pid):
        return pid
    clear_managed_server_pid(root)
    return None


def load_managed_local_server_controller(root: Path) -> EmbeddedServerController | None:
    pid = read_managed_server_pid(root)
    if pid is None:
        pid = detect_listening_pid(get_settings().port)
        if pid is None:
            return None
        write_managed_server_pid(root, pid)
    return EmbeddedServerController(pid=pid, started_by_app=True, root=root)


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def terminate_pid(pid: int) -> None:
    if not is_pid_running(pid):
        return

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGTERM)
    deadline = time.time() + SERVER_SHUTDOWN_WAIT_SECONDS
    while time.time() < deadline:
        if not is_pid_running(pid):
            return
        time.sleep(0.1)
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)


def detect_listening_pid(port: int) -> int | None:
    if sys.platform == "win32":
        command = ["netstat", "-ano", "-p", "tcp"]
    else:
        command = ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    output = completed.stdout.strip()
    if not output:
        return None

    if sys.platform == "win32":
        for line in output.splitlines():
            columns = line.split()
            if len(columns) >= 5 and columns[3].endswith(f":{port}") and columns[4].upper() == "LISTENING":
                try:
                    return int(columns[-1])
                except ValueError:
                    continue
        return None

    first_line = output.splitlines()[0].strip()
    try:
        return int(first_line)
    except ValueError:
        return None


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

    write_managed_server_pid(root, process.pid)
    return EmbeddedServerController(process=process, pid=process.pid, started_by_app=True, root=root)


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
        managed_local_controller = (
            load_managed_local_server_controller(root) if is_local_server_url(remote_server_url) else None
        )
        if managed_local_controller is not None:
            write_startup_trace(root, f"selected managed local server via LAN {remote_server_url}")
            return remote_server_url, managed_local_controller
        write_startup_trace(root, f"selected remote server {remote_server_url}")
        return remote_server_url, EmbeddedServerController()

    if is_server_healthy():
        write_startup_trace(root, "local server is healthy before fallback")
        remote_server_url = discover_healthy_remote_server(root, timeout=DISCOVERY_RECHECK_SECONDS)
        if remote_server_url is not None:
            managed_local_controller = (
                load_managed_local_server_controller(root) if is_local_server_url(remote_server_url) else None
            )
            if managed_local_controller is not None:
                write_startup_trace(root, f"selected managed local server after recheck {remote_server_url}")
                return remote_server_url, managed_local_controller
            write_startup_trace(root, f"selected remote server after recheck {remote_server_url}")
            return remote_server_url, EmbeddedServerController()
        managed_local_controller = load_managed_local_server_controller(root)
        if managed_local_controller is not None:
            write_startup_trace(root, f"selected managed local server {local_server_url()}")
            return local_server_url(), managed_local_controller
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
