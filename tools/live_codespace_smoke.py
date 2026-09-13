#!/usr/bin/env python3
"""Opt-in T1→T2→T3→T4 smoke against one existing Codespace."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

SCHEMA = "cospaces.live-smoke/v1"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--codespace", required=True)
    result.add_argument("--checkpoint-root", default=".")
    result.add_argument("--stop-after", action="store_true")
    result.add_argument("--keep-checkpoint", action="store_true")
    result.add_argument("--json", action="store_true", dest="json_output")
    return result
