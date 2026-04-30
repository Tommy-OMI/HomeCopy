"""Stop the HomeCopy relay server on Windows."""

from __future__ import annotations

import subprocess
import sys


def stop_matching_processes(patterns: list[str], label: str) -> int:
    joined_patterns = "', '".join(patterns)
    powershell_script = f"""
$patterns = @('{joined_patterns}')
$targets = Get-CimInstance Win32_Process |
  Where-Object {{ $_.Name -match '^(python(?:w)?|HomeCopyClient)\\.exe$' }} |
  Where-Object {{ $_.CommandLine }} |
  Where-Object {{
    $commandLine = $_.CommandLine
    foreach ($pattern in $patterns) {{
      if ($commandLine -like "*$pattern*") {{ return $true }}
    }}
    return $false
  }}

if (-not $targets) {{
  Write-Output "[stop] no {label} process is running"
  exit 0
}}

$targets | ForEach-Object {{
  Write-Output ("[stop] stopping PID={{0}} CMD={{1}}" -f $_.ProcessId, $_.CommandLine)
  Stop-Process -Id $_.ProcessId -Force
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell_script],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def main() -> None:
    raise SystemExit(
        stop_matching_processes(
            [
                "homecopy.server.app:app",
                "--server-mode",
            ],
            "relay-server",
        )
    )


if __name__ == "__main__":
    main()
