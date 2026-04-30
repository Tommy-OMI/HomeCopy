from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessingConfig:
    server_id: str
    dropbox_root: Path
    work_dir: Path
    log_dir: Path
    stable_after_minutes: int = 10
    auto_ready_after_hours: int = 0
    max_scan_files: int = 10000


def load_config(path: Path) -> ProcessingConfig:
    raw = _parse_simple_yaml(path)
    required = ["server_id", "dropbox_root", "work_dir", "log_dir"]
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"Missing config fields: {', '.join(missing)}")

    return ProcessingConfig(
        server_id=str(raw["server_id"]),
        dropbox_root=Path(str(raw["dropbox_root"])),
        work_dir=Path(str(raw["work_dir"])),
        log_dir=Path(str(raw["log_dir"])),
        stable_after_minutes=int(raw.get("stable_after_minutes", 10)),
        auto_ready_after_hours=int(raw.get("auto_ready_after_hours", 0)),
        max_scan_files=int(raw.get("max_scan_files", 10000)),
    )


def _parse_simple_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    values: dict[str, object] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"Invalid config line {line_number}: {line}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if value.lower() in {"true", "false"}:
            values[key] = value.lower() == "true"
        else:
            try:
                values[key] = int(value)
            except ValueError:
                values[key] = value

    return values

