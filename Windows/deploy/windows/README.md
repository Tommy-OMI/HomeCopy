# Windows Deployment Notes

The current server deployment target is a GitHub self-hosted runner on the preprocessing machine.

Recommended machine-local config path:

```text
D:\OMI\config\processing-server.yaml
```

The first bootstrap workflow only verifies:

- Python package installation.
- Unit tests.
- CLI health.
- Optional scan of `D:\OMI\config\processing-server.yaml` if that file exists.

The OMI Processing Server is not installed as a Windows Service yet. During this phase, GitHub Actions starts CLI commands directly.

