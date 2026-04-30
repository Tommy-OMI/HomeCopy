"""Client configuration loader."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from homecopy.shared.constants import DEFAULT_HISTORY_LIMIT
from homecopy.shared.models import normalize_device_id


PLACEHOLDER_AUTH_TOKEN = "replace-with-a-long-random-secret"
DEFAULT_GLOBAL_HOTKEY = "Ctrl+Alt+K"
LEGACY_WINDOWS_HOTKEYS = {"Ctrl+Alt+H"}


def make_device_id(device_name: str) -> str:
    device_id = "".join(char.lower() if char.isalnum() else "-" for char in device_name).strip("-")
    while "--" in device_id:
        device_id = device_id.replace("--", "-")
    return (device_id or "local-device")[:48]


class ClientConfig(BaseModel):
    device_id: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    device_name: str = Field(min_length=1, max_length=100)
    server_url: str = Field(min_length=1)
    auth_token: str = ""
    minimize_to_tray: bool = True
    global_hotkey: str = DEFAULT_GLOBAL_HOTKEY
    auto_start_server_if_missing: bool = True
    auto_copy_on_receive: bool = True
    show_notification: bool = True
    history_limit: int = Field(default=DEFAULT_HISTORY_LIMIT, ge=1, le=1000)
    history_path: Path = Path("client_history.json")
    setup_completed: bool = False

    @field_validator("device_id")
    @classmethod
    def normalize_config_device_id(cls, value: str) -> str:
        return normalize_device_id(value)

    @classmethod
    def load(cls, path: str | Path) -> "ClientConfig":
        config_path = Path(path)
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if data.get("global_hotkey") in LEGACY_WINDOWS_HOTKEYS:
            data["global_hotkey"] = DEFAULT_GLOBAL_HOTKEY
        base_dir = config_path.parent
        if "history_path" in data:
            data["history_path"] = base_dir / data["history_path"]
        else:
            data["history_path"] = base_dir / "client_history.json"
        return cls.model_validate(data)

    @classmethod
    def build_default(cls, path: str | Path, server_url: str, auth_token: str) -> "ClientConfig":
        config_path = Path(path)
        device_name = socket.gethostname() or "Local Windows"
        return cls(
            device_id=make_device_id(device_name),
            device_name=device_name[:100],
            server_url=server_url,
            auth_token=auth_token,
            history_path=config_path.parent / "client_history.json",
            setup_completed=False,
        )

    def save(self, path: str | Path) -> None:
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.model_dump(mode="json")

        history_path = Path(payload["history_path"])
        try:
            payload["history_path"] = str(history_path.relative_to(config_path.parent))
        except ValueError:
            payload["history_path"] = str(history_path)

        config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def needs_first_run_setup(self) -> bool:
        return not self.setup_completed
