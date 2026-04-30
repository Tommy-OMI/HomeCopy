# OMI Processing Server

Python CLI for the OMI Astera preprocessing machine. Dropbox Desktop is responsible for syncing files; this service only scans local Dropbox folders, detects target readiness, and later runs preprocessing jobs.

## Commands

```powershell
py -m pip install -e .
omi-processing health --json
omi-processing scan --config D:\OMI\config\processing-server.yaml --json
omi-processing process-once --config D:\OMI\config\processing-server.yaml --dry-run
```

## Config

Copy `config.example.yaml` to a machine-local path such as:

```text
D:\OMI\config\processing-server.yaml
```

Do not commit the real config file. It contains machine paths.

## Target Readiness

A target folder is considered ready when:

- It contains at least one FITS file.
- Every FITS file is older than `stable_after_minutes`.
- The folder contains `omi_complete.json`.

If `omi_complete.json` is missing but the folder has been stable for `auto_ready_after_hours`, the scanner reports `stable` instead of `ready` unless `auto_ready_after_hours` is explicitly set above zero.

