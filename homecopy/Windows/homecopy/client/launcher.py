"""Shared launcher helpers for script and packaged GUI startup."""

from __future__ import annotations

import argparse
from pathlib import Path

from homecopy.client.config import ClientConfig
from homecopy.paths import runtime_data_root
from homecopy.client.startup import prepare_client_config
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


def launch_gui(config_arg: str | None = None) -> None:
    root = runtime_data_root()
    config_path = resolve_config_path(config_arg)
    prepare_client_config(config_path, root)
    app, window = create_application(config_path)
    window.show()
    app.exec()
