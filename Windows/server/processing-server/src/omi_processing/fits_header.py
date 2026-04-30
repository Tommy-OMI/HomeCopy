from __future__ import annotations

from pathlib import Path


HEADER_KEYS = ("FILTER", "EXPTIME", "EXPOSURE", "OBJECT", "IMAGETYP")
MAX_HEADER_BLOCKS = 32
FITS_BLOCK_SIZE = 2880
FITS_CARD_SIZE = 80


def read_fits_metadata(path: Path) -> dict[str, object]:
    try:
        header = _read_header_cards(path)
    except OSError:
        return {}

    metadata: dict[str, object] = {}
    for key in HEADER_KEYS:
        if key in header:
            metadata[key.lower()] = header[key]

    exposure = metadata.get("exptime", metadata.get("exposure", 0))
    metadata["exposure_seconds"] = _to_float(exposure)
    return metadata


def _read_header_cards(path: Path) -> dict[str, object]:
    cards: dict[str, object] = {}
    with path.open("rb") as handle:
        for _ in range(MAX_HEADER_BLOCKS):
            block = handle.read(FITS_BLOCK_SIZE)
            if not block:
                break

            text = block.decode("ascii", errors="ignore")
            for offset in range(0, len(text), FITS_CARD_SIZE):
                card = text[offset : offset + FITS_CARD_SIZE]
                key = card[:8].strip()
                if key == "END":
                    return cards
                if key in HEADER_KEYS and "=" in card:
                    raw_value = card.split("=", 1)[1].split("/", 1)[0].strip()
                    cards[key] = _parse_card_value(raw_value)

    return cards


def _parse_card_value(raw_value: str) -> object:
    if raw_value.startswith("'") and "'" in raw_value[1:]:
        return raw_value[1:].split("'", 1)[0].strip()

    normalized = raw_value.strip()
    if normalized in {"T", "F"}:
        return normalized == "T"

    try:
        if "." in normalized or "E" in normalized.upper():
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized


def _to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

