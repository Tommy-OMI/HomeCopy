"""Shared launcher helpers for script and packaged GUI startup."""

from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from homecopy.client.config import ClientConfig
from homecopy.client.ui.setup_dialog import SetupDialog
from homecopy_shared.startup_policy import MissingServerResolution, local_server_url, prepare_client_launch
from homecopy.paths import runtime_data_root
from homecopy.client.ui.main_window import create_application


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HomeCopy desktop client")
    parser.add_argument("--config", default=None, help="Optional path to a client config.json")
    parser.add_argument("--server-mode", action="store_true", help="Run the embedded relay server only")
    return parser.parse_args()


def resolve_missing_server_with_setup(
    config_path: Path,
    config: ClientConfig,
) -> MissingServerResolution:
    dialog = SetupDialog(
        config,
        config_path,
        server_missing=True,
        local_server_url=local_server_url(),
    )
    if dialog.exec() != QDialog.Accepted:
        return MissingServerResolution(action="cancel")
    return MissingServerResolution(
        action=dialog.result_payload.action,
        server_url=dialog.result_payload.server_url,
    )


def launch_gui(config_arg: str | None = None) -> None:
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    root = runtime_data_root()
    config_path = resolve_config_path(config_arg)

    try:
        launch_context = prepare_client_launch(
            config_path,
            root,
            resolve_missing_server=resolve_missing_server_with_setup,
        )
    except RuntimeError as exc:
        QMessageBox.information(None, "HomeCopy", str(exc))
        return

    app.aboutToQuit.connect(lambda: launch_context.server_controller.shutdown())

    try:
        app, window = create_application(
            launch_context.config_path,
            launch_context.config,
            launch_context.server_controller,
        )
        app.setQuitOnLastWindowClosed(True)
        window.show()
        app.exec()
    finally:
        launch_context.server_controller.shutdown()
