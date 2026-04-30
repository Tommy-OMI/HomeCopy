"""Stop local HomeCopy server and client processes on Windows."""

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
  Write-Output "[stop] no {label} processes are running"
  exit 0
}}

$targets | Sort-Object ProcessId -Unique | ForEach-Object {{
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
    patterns = [
        "homecopy.server.app:app",
        "-m homecopy.client.main",
        "-m homecopy.client.gui_main",
        "-m homecopy.client.launcher_main",
        "--server-mode",
        "scripts\\start_server.py",
        "scripts\\start_client.py",
    ]
    raise SystemExit(stop_matching_processes(patterns, "HomeCopy"))


if __name__ == "__main__":
    main()
