"""Compatibility wrappers around the unified client startup policy."""

from __future__ import annotations

from pathlib import Path

from homecopy.client.config import ClientConfig
from homecopy_shared.startup_policy import (
    ConfirmStartServer,
    prepare_client_launch,
    resolve_runtime_server,
)


def resolve_runtime_server_url(
    config_path: Path,
    root: Path,
    confirm_start_server: ConfirmStartServer | None = None,
) -> str:
    config = ClientConfig.load(config_path)
    server_url, _ = resolve_runtime_server(
        config_path,
        root,
        config,
        confirm_start_server=confirm_start_server,
    )
    return server_url


def prepare_client_config(
    config_path: Path,
    root: Path,
    confirm_start_server: ConfirmStartServer | None = None,
) -> ClientConfig:
    return prepare_client_launch(
        config_path,
        root,
        confirm_start_server=confirm_start_server,
    ).config
