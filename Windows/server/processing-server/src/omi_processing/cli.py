from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .formatting import format_bytes, format_duration
from .scanner import scan_dropbox_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omi-processing")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser("health", help="Show local CLI health information.")
    health_parser.add_argument("--json", action="store_true", dest="as_json")

    scan_parser = subparsers.add_parser("scan", help="Scan target folders below the Dropbox root.")
    _add_config_args(scan_parser)
    scan_parser.add_argument("--limit", type=int, default=None)

    process_parser = subparsers.add_parser("process-once", help="Find ready folders and dry-run one processing pass.")
    _add_config_args(process_parser)
    process_parser.add_argument("--dry-run", action="store_true", default=False)

    args = parser.parse_args(argv)

    try:
        if args.command == "health":
            return _health(args.as_json)
        if args.command == "scan":
            return _scan(args.config, args.as_json, args.limit)
        if args.command == "process-once":
            return _process_once(args.config, args.as_json, args.dry_run)
    except Exception as exc:  # pragma: no cover - keeps CLI failures clear in Actions logs.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def _add_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")


def _health(as_json: bool) -> int:
    payload = {
        "ok": True,
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"OMI Processing Server CLI {payload['version']}")
        print(f"Python {payload['python']}")
        print(payload["platform"])
    return 0


def _scan(config_path: Path, as_json: bool, limit: int | None) -> int:
    config = load_config(config_path)
    targets = scan_dropbox_root(config, limit=limit)
    payload = {
        "serverId": config.server_id,
        "dropboxRoot": str(config.dropbox_root),
        "targetCount": len(targets),
        "targets": [target.to_dict() for target in targets],
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        _print_targets(payload)
    return 0


def _process_once(config_path: Path, as_json: bool, dry_run: bool) -> int:
    config = load_config(config_path)
    targets = scan_dropbox_root(config)
    ready_targets = [target for target in targets if target.status == "ready"]
    payload = {
        "serverId": config.server_id,
        "dryRun": dry_run,
        "readyTargetCount": len(ready_targets),
        "readyTargets": [target.to_dict() for target in ready_targets],
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Ready targets: {len(ready_targets)}")
        for target in ready_targets:
            print(f"- {target.name} ({target.fits_count} FITS)")
        if dry_run:
            print("Dry run only; no processing job was started.")
        else:
            print("Processing engine is not connected yet; no files were modified.")
    return 0


def _print_targets(payload: dict[str, object]) -> None:
    print(f"Server: {payload['serverId']}")
    print(f"Dropbox root: {payload['dropboxRoot']}")
    print(f"Targets: {payload['targetCount']}")
    for target in payload["targets"]:
        channel_text = ", ".join(
            f"{channel['name']} {channel['fitsCount']} / {format_duration(channel['exposureSeconds'])}"
            for channel in target["channels"]
        )
        print(
            f"- {target['name']}: {target['status']}, "
            f"{target['fitsCount']} FITS, {format_bytes(target['totalSizeBytes'])}"
        )
        if channel_text:
            print(f"  {channel_text}")


if __name__ == "__main__":
    raise SystemExit(main())

