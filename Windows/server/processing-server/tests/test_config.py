from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from omi_processing.config import load_config


class ConfigTests(TestCase):
    def test_loads_simple_yaml_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        'server_id: "worker-test"',
                        f'dropbox_root: "{temp_dir}"',
                        f'work_dir: "{temp_dir}/work"',
                        f'log_dir: "{temp_dir}/logs"',
                        "stable_after_minutes: 12",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.server_id, "worker-test")
            self.assertEqual(config.stable_after_minutes, 12)

