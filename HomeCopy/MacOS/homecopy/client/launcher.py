"""Shared launcher helpers for script and packaged GUI startup."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from homecopy.client.config import ClientConfig
from homecopy_shared.startup_policy import prepare_client_launch
from homecopy.paths import runtime_data_root


def ensure_bootstrap_config(root: Path) -> Path:
    config_path = root / "configs" / "clients" / "client.local.json"
    if not config_path.exists():
        config = ClientConfig.build_default(
            config_path,
            server_url="ws://127.0.0.1:8765/ws",
            auth_token="",
        )
        config.save(config_path)
    return config_path


def resolve_config_path(config_arg: str | None) -> Path:
    root = runtime_data_root()
    if config_arg:
        candidate = Path(config_arg)
        return candidate if candidate.is_absolute() else (root / candidate).resolve()

    config_dir = root / "configs" / "clients"
    config_candidates = sorted(config_dir.glob("*.json"))
    if config_candidates:
        return config_candidates[0]
    return ensure_bootstrap_config(root)


def confirm_local_server_start() -> bool:
    message = (
        "No HomeCopy server was found on the local network.\n\n"
        "Start a local relay server on this machine and connect to it?"
    )
    result = QMessageBox.question(
        None,
        "HomeCopy",
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    return result == QMessageBox.Yes


def launch_gui(config_arg: str | None = None) -> None:
    from homecopy.client.ui.main_window import create_application

    app = QApplication.instance() or QApplication([])
    root = runtime_data_root()
    config_path = resolve_config_path(config_arg)

    try:
        launch_context = prepare_client_launch(
            config_path,
            root,
            confirm_start_server=confirm_local_server_start,
        )
    except RuntimeError as exc:
        QMessageBox.information(None, "HomeCopy", str(exc))
        return

    app.aboutToQuit.connect(launch_context.server_controller.shutdown)

    try:
        app, window = create_application(
            launch_context.config_path,
            launch_context.config,
            launch_context.server_controller,
        )
        window.show()
        app.exec()
    finally:
        launch_context.server_controller.shutdown()
