"""Launcher entrypoint suitable for both source runs and packaged executables."""

from __future__ import annotations

from homecopy.client.launcher import launch_gui, parse_args
from homecopy.server.runner import run_server


def main() -> None:
    args = parse_args()
    if getattr(args, "server_mode", False):
        run_server()
        return

    launch_gui(args.config)


if __name__ == "__main__":
    main()
