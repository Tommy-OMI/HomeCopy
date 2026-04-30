#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  SELECTED_PYTHON_BIN="$PYTHON_BIN"
else
  for candidate in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      SELECTED_PYTHON_BIN="$(command -v "$candidate")"
      break
    fi
  done
fi

if [[ -z "${SELECTED_PYTHON_BIN:-}" ]]; then
  echo "Unable to find a supported Python interpreter for macOS packaging." >&2
  exit 1
fi

PYTHON_BIN="$SELECTED_PYTHON_BIN"
VENV_DIR=".venv-packaging"

echo "Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -V

rm -rf "$VENV_DIR"
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
  --paths "$(pwd)/../Common" \
  --collect-all pynput \
  --collect-submodules homecopy \
  --collect-submodules homecopy_shared \
  homecopy/client/launcher_main.py

APP_PLIST="dist/HomeCopyClient.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.omi.homecopyclient" "$APP_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.omi.homecopyclient" "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Add :NSLocalNetworkUsageDescription string HomeCopy connects to other devices on your local network to discover relay servers and exchange clipboard text." "$APP_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :NSLocalNetworkUsageDescription HomeCopy connects to other devices on your local network to discover relay servers and exchange clipboard text." "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity dict" "$APP_PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSAllowsLocalNetworking bool true" "$APP_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :NSAppTransportSecurity:NSAllowsLocalNetworking true" "$APP_PLIST"

PACKAGE_DIR="dist/HomeCopyClient-macOS"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

cp -R "dist/HomeCopyClient.app" "$PACKAGE_DIR/"
cp ".env.example" "$PACKAGE_DIR/.env.example"

echo "macOS package ready at $PACKAGE_DIR"
echo "Copy the whole directory and run HomeCopyClient.app on a Mac."
