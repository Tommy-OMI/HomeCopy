"""Console entry point for the HomeCopy installer."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import __version__
from .config import GET_PIP_URL, configured_ref
from .github import download_source_tree, read_app_version, resolve_remote_source
from .metadata import build_metadata, load_metadata, save_metadata
from .paths import data_root, installed_app_path, installer_root, source_path, staged_source_path
from .platforms.macos import build_and_install as build_and_install_macos
from .platforms.windows import build_and_install as build_and_install_windows
from .python_runtime import select_build_python
from .utils import ensure_directory, promote_tree, remove_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homecopy", description="Install and update HomeCopy.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Download, build, and install HomeCopy.")
    install_parser.add_argument("--ref", default=configured_ref(), help="Git ref to install.")
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if the installed commit already matches the remote commit.",
    )

    update_parser = subparsers.add_parser("update", help="Update HomeCopy from GitHub.")
    update_parser.add_argument("--ref", default=configured_ref(), help="Git ref to update from.")
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if the installed commit already matches the remote commit.",
    )

    subparsers.add_parser("doctor", help="Show local installer diagnostics.")
    subparsers.add_parser("version", help="Show installer and installed app versions.")
    return parser


def ensure_supported_platform() -> None:
    if sys.platform not in {"darwin", "win32"}:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


def ensure_pip_available() -> str:
    version = _pip_version()
    if version:
        return version

    print("[setup] pip not found; trying ensurepip")
    try:
        subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.SubprocessError:
        print("[setup] ensurepip unavailable; downloading get-pip.py")
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "get-pip.py"
            with urllib.request.urlopen(GET_PIP_URL, timeout=60) as response, script_path.open("wb") as file_obj:
                file_obj.write(response.read())
            subprocess.run([sys.executable, str(script_path)], check=True)

    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    version = _pip_version()
    if not version:
        raise RuntimeError("pip could not be initialized on this machine.")
    return version


def _pip_version() -> str | None:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.SubprocessError:
        return None
    return completed.stdout.strip()


def select_builder():
    if sys.platform == "darwin":
        return build_and_install_macos
    if sys.platform == "win32":
        return build_and_install_windows
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def install_or_update(*, ref: str, force: bool) -> int:
    ensure_supported_platform()
    ensure_directory(installer_root())
    ensure_directory(data_root())
    pip_version = ensure_pip_available()
    build_python = select_build_python()
    print(f"[setup] {pip_version}")
    print(f"[setup] build_python={build_python.display} ({build_python.version})")

    remote = resolve_remote_source(ref)
    current = load_metadata()
    if current and current.commit == remote.commit and not force:
        print(f"HomeCopy is already up to date at {current.commit[:7]} ({current.app_version}).")
        print(f"Installed app: {current.installed_path}")
        return 0

    with tempfile.TemporaryDirectory(prefix="homecopy-install-") as temp_dir:
        temp_root = Path(temp_dir)
        extracted_root = download_source_tree(remote, temp_root)
        staged_root = staged_source_path()
        remove_path(staged_root)
        shutil.copytree(extracted_root, staged_root)

        app_version = read_app_version(staged_root)
        install_target = select_builder()(staged_root, build_python)
        remove_path(source_path())
        promote_tree(staged_root, source_path())

    metadata = build_metadata(
        app_version=app_version,
        commit=remote.commit,
        installed_path=install_target,
        platform=sys.platform,
        ref=remote.ref,
        repo=remote.repo_url,
        source_path=source_path(),
    )
    save_metadata(metadata)

    print(f"Installed HomeCopy {app_version} from {remote.commit[:7]}.")
    print(f"Installed app: {install_target}")
    return 0


def doctor() -> int:
    ensure_supported_platform()
    print(f"platform: {sys.platform}")
    print(f"python: {sys.executable}")
    print(f"python_version: {sys.version.split()[0]}")
    pip_version = ensure_pip_available()
    build_python = select_build_python()
    print(f"pip: {pip_version}")
    print(f"build_python: {build_python.display} ({build_python.version})")
    print(f"data_root: {data_root()}")
    print(f"installer_root: {installer_root()}")
    print(f"source_path: {source_path()} ({'present' if source_path().exists() else 'missing'})")
    print(
        f"installed_target: {installed_app_path()} "
        f"({'present' if installed_app_path().exists() else 'missing'})"
    )

    metadata = load_metadata()
    if metadata:
        print(f"installed_commit: {metadata.commit}")
        print(f"installed_version: {metadata.app_version}")
    else:
        print("installed_commit: none")
        print("installed_version: none")

    try:
        remote = resolve_remote_source(configured_ref())
    except Exception as exc:
        print(f"remote_check: failed ({exc})")
    else:
        print(f"remote_ref: {remote.ref}")
        print(f"remote_commit: {remote.commit}")

    return 0


def version() -> int:
    print(f"homecopy-installer {__version__}")
    metadata = load_metadata()
    if metadata:
        print(f"installed-app {metadata.app_version} ({metadata.commit[:7]})")
        print(f"installed-path {metadata.installed_path}")
    else:
        print("installed-app not installed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "install":
        return install_or_update(ref=args.ref, force=args.force)
    if args.command == "update":
        return install_or_update(ref=args.ref, force=args.force)
    if args.command == "doctor":
        return doctor()
    if args.command == "version":
        return version()

    parser.error(f"Unsupported command: {args.command}")
    return 2
