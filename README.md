# HomeCopy

HomeCopy is a desktop text relay app for macOS and Windows.

This repository now ships a small Python installer CLI so a machine can pull the
latest HomeCopy source from GitHub, build the local executable, and update it later.

## Install the installer

```bash
pip install HomeCopy
```

If you are working from a local source checkout and want this machine to expose
the `homecopy` command directly from the repo:

```bash
python3 scripts/install_local_cli.py
```

If `pip` is missing but Python is already installed:

```bash
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip
```

On Windows:

```powershell
py -m ensurepip --upgrade
py -m pip install --upgrade pip
```

## Build the desktop app locally

```bash
homecopy install
```

This command:

- downloads the latest `Tommy-OMI/HomeCopy` source from GitHub
- builds the platform-specific desktop executable on the current machine
- installs the built app into a local user-owned directory

The installer prefers Python `3.12` or `3.11` for the actual desktop build.
If you want to force a specific interpreter:

```bash
export HOMECOPY_PYTHON_BIN=/path/to/python3.11
homecopy install
```

## Update to the latest GitHub version

```bash
homecopy update
```

## Diagnostics

```bash
homecopy doctor
homecopy version
```

## Installed paths

- macOS app target: `~/Applications/HomeCopy.app`
- macOS data root: `~/Library/Application Support/HomeCopy`
- Windows app target: `%LOCALAPPDATA%\Programs\HomeCopy`
- Windows data root: `%LOCALAPPDATA%\HomeCopy`

## Source layout

- `Common/`: shared cross-platform modules
- `MacOS/`: macOS client and server sources plus macOS packaging script
- `Windows/`: Windows client and server sources plus Windows packaging script
- `src/homecopy_installer/`: pip-installed installer CLI
