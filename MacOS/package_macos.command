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
RECREATE_VENV=0

echo "Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -V

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  RECREATE_VENV=1
fi

if [[ "$RECREATE_VENV" -eq 1 ]]; then
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [[ "$RECREATE_VENV" -eq 1 ]]; then
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install pyinstaller
  python -m pip install -r requirements.txt
fi

rm -rf build dist

python -m PyInstaller \
  --noconfirm \
  --clean \
  HomeCopyClient.spec

APP_PLIST="dist/HomeCopyClient.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.omi.homecopyclient" "$APP_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.omi.homecopyclient" "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Add :NSLocalNetworkUsageDescription string HomeCopy connects to other devices on your local network to discover relay servers and exchange clipboard text." "$APP_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :NSLocalNetworkUsageDescription HomeCopy connects to other devices on your local network to discover relay servers and exchange clipboard text." "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity dict" "$APP_PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSAllowsLocalNetworking bool true" "$APP_PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :NSAppTransportSecurity:NSAllowsLocalNetworking true" "$APP_PLIST"

codesign --force --deep --strict --options runtime \
  --entitlements "HomeCopyClient.entitlements" \
  -s "01E87028BADEF4155CDAC15B4C40657146D110C1" \
  "dist/HomeCopyClient.app"

PACKAGE_DIR="dist/HomeCopyClient-macOS"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

cp -R "dist/HomeCopyClient.app" "$PACKAGE_DIR/"
cp ".env.example" "$PACKAGE_DIR/.env.example"

echo "macOS package ready at $PACKAGE_DIR"
echo "Copy the whole directory and run HomeCopyClient.app on a Mac."

SHARED_DIR="$HOME/Shared"
mkdir -p "$SHARED_DIR"
rm -rf "$SHARED_DIR/HomeCopyClient.app"
cp -R "dist/HomeCopyClient.app" "$SHARED_DIR/"
echo "Copied HomeCopyClient.app -> $SHARED_DIR/"
