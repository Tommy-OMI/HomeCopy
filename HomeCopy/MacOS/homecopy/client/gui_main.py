"""Desktop GUI entrypoint for the HomeCopy client."""

from __future__ import annotations

import argparse

from homecopy.client.ui.main_window import create_application


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HomeCopy desktop client")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app, window = create_application(args.config)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
