"""Helpers for running the embedded HomeCopy server."""

from __future__ import annotations

import uvicorn

from homecopy.server.config import get_settings


def run_server() -> None:
    settings = get_settings()
    uvicorn.run(
        "homecopy.server.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        use_colors=False,
    )


if __name__ == "__main__":
    run_server()
