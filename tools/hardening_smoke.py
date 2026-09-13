#!/usr/bin/env python3
"""Run the network-free Phase 1 MVP hardening suite and emit one JSON record."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "cospaces.hardening/v1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    command = (sys.executable, "-m", "pytest", "-q", "tests/hardening")
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    payload = {
        "schema": SCHEMA,
        "ok": completed.returncode == 0,
        "live_codespace": False,
        "command": list(command),
        "exit_code": completed.returncode,
        "duration_seconds": max(0.0, time.monotonic() - started),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if args.json_output:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    else:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
