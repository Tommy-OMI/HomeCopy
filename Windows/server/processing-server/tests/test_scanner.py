import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from omi_processing.config import ProcessingConfig
from omi_processing.scanner import scan_dropbox_root


class ScannerTests(TestCase):
    def test_scans_targets_and_groups_channel_stats(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "M31"
            target.mkdir()
            _write_minimal_fits(target / "m31_l_001.fit", filter_name="L", exposure=300)
            _write_minimal_fits(target / "m31_l_002.fit", filter_name="L", exposure=300)
            _write_minimal_fits(target / "m31_ha_001.fits", filter_name="Ha", exposure=600)
            (target / "omi_complete.json").write_text("{}", encoding="utf-8")

            old_time = time.time() - 3600
            for file_path in target.glob("*.fit*"):
                os.utime(file_path, (old_time, old_time))

            config = ProcessingConfig(
                server_id="test",
                dropbox_root=root,
                work_dir=root / "work",
                log_dir=root / "logs",
                stable_after_minutes=10,
            )

            targets = scan_dropbox_root(config)

            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0].status, "ready")
            self.assertEqual(targets[0].fits_count, 3)
            channel_map = {channel.name: channel for channel in targets[0].channels}
            self.assertEqual(channel_map["L"].fits_count, 2)
            self.assertEqual(channel_map["L"].exposure_seconds, 600)
            self.assertEqual(channel_map["Ha"].fits_count, 1)
            self.assertEqual(channel_map["Ha"].exposure_seconds, 600)


def _write_minimal_fits(path: Path, *, filter_name: str, exposure: int) -> None:
    cards = [
        _card("SIMPLE", "T"),
        _card("BITPIX", "8"),
        _card("NAXIS", "0"),
        _card("FILTER", f"'{filter_name}'"),
        _card("EXPTIME", str(exposure)),
        "END".ljust(80),
    ]
    header = "".join(cards).encode("ascii")
    padding = b" " * (2880 - len(header))
    path.write_bytes(header + padding)


def _card(key: str, value: str) -> str:
    return f"{key:<8}= {value:<20}".ljust(80)

