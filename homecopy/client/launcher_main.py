"""Launcher entrypoint suitable for both source runs and packaged executables."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HomeCopy desktop client")
    parser.add_argument("--config", default=None, help="Optional path to a client config.json")
    parser.add_argument("--server-mode", action="store_true", help="Run the embedded relay server only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if getattr(args, "server_mode", False):
        from homecopy.server.runner import run_server

        run_server()
        return

    from homecopy.client.launcher import launch_gui

    launch_gui(args.config)


if __name__ == "__main__":
    main()
