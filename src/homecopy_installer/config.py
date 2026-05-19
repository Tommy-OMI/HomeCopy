"""Static installer configuration."""

from __future__ import annotations

import os


REPO_OWNER = "Tommy-OMI"
REPO_NAME = "HomeCopy"
DEFAULT_REF = "main"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_ARCHIVE_BASE = "https://codeload.github.com"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def configured_ref() -> str:
    return os.environ.get("HOMECOPY_REPO_REF", DEFAULT_REF)
