"""GitHub download helpers for the installer."""

from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_REF, GITHUB_API_BASE, GITHUB_ARCHIVE_BASE, REPO_NAME, REPO_OWNER


VERSION_PATTERN = re.compile(r'APP_VERSION\s*=\s*"([^"]+)"')


@dataclass(frozen=True)
class RemoteSource:
    archive_url: str
    commit: str
    ref: str
    repo_url: str


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HomeCopyInstaller/0.10.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _read_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def resolve_remote_source(ref: str | None = None) -> RemoteSource:
    selected_ref = ref or DEFAULT_REF
    payload = _read_json(
        f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits/{selected_ref}"
    )
    commit = payload["sha"]
    return RemoteSource(
        archive_url=f"{GITHUB_ARCHIVE_BASE}/{REPO_OWNER}/{REPO_NAME}/zip/{commit}",
        commit=commit,
        ref=selected_ref,
        repo_url=f"https://github.com/{REPO_OWNER}/{REPO_NAME}",
    )


def download_source_tree(remote: RemoteSource, working_directory: Path) -> Path:
    archive_path = working_directory / "source.zip"
    extract_root = working_directory / "extract"
    extract_root.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(remote.archive_url, headers=_headers())
    with urllib.request.urlopen(request, timeout=120) as response, archive_path.open("wb") as file_obj:
        shutil.copyfileobj(response, file_obj)

    with zipfile.ZipFile(archive_path) as zip_file:
        zip_file.extractall(extract_root)

    roots = [path for path in extract_root.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one extracted source directory, found {len(roots)}")
    return roots[0]


def read_app_version(source_root: Path) -> str:
    init_path = source_root / "Common" / "homecopy_shared" / "__init__.py"
    match = VERSION_PATTERN.search(init_path.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"Unable to read APP_VERSION from {init_path}")
    return match.group(1)
