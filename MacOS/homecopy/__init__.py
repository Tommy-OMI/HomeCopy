"""HomeCopy package."""

from __future__ import annotations

import sys
from pathlib import Path


def _add_shared_module_path() -> None:
    shared_root = Path(__file__).resolve().parents[2] / "Common"
    if shared_root.is_dir():
        shared_root_text = str(shared_root)
        if shared_root_text not in sys.path:
            sys.path.insert(0, shared_root_text)


_add_shared_module_path()
