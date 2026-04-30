"""Environment-backed configuration for the relay server."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from homecopy.paths import runtime_env_path
from homecopy.shared.constants import DEFAULT_MAX_TEXT_LENGTH

load_dotenv(runtime_env_path())


class ServerSettings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8765, ge=1, le=65535)
    auth_token: str = Field(default="")
    log_level: str = Field(default="INFO")
    max_text_length: int = Field(default=DEFAULT_MAX_TEXT_LENGTH, ge=1, le=100000)
    discovery_enabled: bool = True
    discovery_port: int = Field(default=8766, ge=1, le=65535)
    discovery_interval: float = Field(default=2.0, ge=0.5, le=60.0)
    discovery_advertise_host: str = ""


@lru_cache(maxsize=1)
def get_settings() -> ServerSettings:
    return ServerSettings(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8765")),
        auth_token=os.getenv("AUTH_TOKEN", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        max_text_length=int(os.getenv("MAX_TEXT_LENGTH", str(DEFAULT_MAX_TEXT_LENGTH))),
        discovery_enabled=os.getenv("DISCOVERY_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
        discovery_port=int(os.getenv("DISCOVERY_PORT", "8766")),
        discovery_interval=float(os.getenv("DISCOVERY_INTERVAL", "2.0")),
        discovery_advertise_host=os.getenv("DISCOVERY_ADVERTISE_HOST", ""),
    )
