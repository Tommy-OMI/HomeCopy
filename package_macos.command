#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv-packaging"

"$PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install pyinstaller
python -m pip install -r requirements.txt

rm -rf build dist

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name HomeCopyClient \
  --paths "$(pwd)" \
  --collect-all pynput \
  --collect-submodules homecopy \
  homecopy/client/launcher_main.py

PACKAGE_DIR="dist/HomeCopyClient-macOS"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

cp -R "dist/HomeCopyClient.app" "$PACKAGE_DIR/"
cp ".env.example" "$PACKAGE_DIR/.env.example"

echo "macOS package ready at $PACKAGE_DIR"
echo "Copy the whole directory and run HomeCopyClient.app on a Mac."
