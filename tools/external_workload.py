#!/usr/bin/env python3
"""Bounded, repository-owned workload for external host qualification."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    import resource
except ImportError:  # pragma: no cover - unavailable on Windows
    resource = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cospaces.external-workload/v1"
MAX_REPETITIONS = 24
MAX_INTERVAL_SECONDS = 3600.0
MAX_STAGE_TIMEOUT_SECONDS = 3600.0
MAX_DIAGNOSTIC_BYTES = 8192


@dataclass(frozen=True)
class Stage:
    name: str
    argv: tuple[str, ...]


PROFILES: dict[str, tuple[Stage, ...]] = {
    "smoke": (
        Stage("module_help", ("{python}", "-m", "cospaces", "--help")),
    ),
    "core": (
        Stage("hardening", ("{python}", "tools/hardening_smoke.py", "--json")),
        Stage(
            "build",
            (
                "{python}",
                "-m",
                "build",
                "--no-isolation",
                "--outdir",
                "{build_out}",
            ),
        ),
    ),
    "full": (
        Stage("ruff_lint", ("{python}", "-m", "ruff", "check", ".")),
        Stage("ruff_format", ("{python}", "-m", "ruff", "format", "--check", ".")),
        Stage("mypy", ("{python}", "-m", "mypy", "src/cospaces")),
        Stage("pytest", ("{python}", "-m", "pytest")),
        Stage("hardening", ("{python}", "tools/hardening_smoke.py", "--json")),
        Stage(
            "build",
            (
                "{python}",
                "-m",
                "build",
                "--no-isolation",
                "--outdir",
                "{build_out}",
            ),
        ),
        Stage("module_help", ("{python}", "-m", "cospaces", "--help")),
        Stage("console_help", ("cospaces", "--help")),
    ),
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_average() -> list[float] | None:
    try:
        return [round(value, 3) for value in os.getloadavg()]
    except (AttributeError, OSError):
        return None


def _free_space_bytes() -> int | None:
    try:
        return shutil.disk_usage(ROOT).free
    except OSError:
        return None


def _child_cpu() -> tuple[float, float] | None:
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime, usage.ru_stime


def _git_text(*arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ("git", *arguments),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def source_context() -> dict[str, object]:
    commit = _git_text("rev-parse", "HEAD")
    status = _git_text("status", "--porcelain=v1", "--untracked-files=normal")
    return {
        "commit": commit,
        "dirty": None if status is None else bool(status),
    }


def environment_context() -> dict[str, object]:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }


def display_argv(stage: Stage) -> list[str]:
    return [
        "python" if item == "{python}" else "<scratch>/build" if item == "{build_out}" else item
        for item in stage.argv
    ]


def expand_argv(stage: Stage, scratch: Path) -> tuple[str, ...]:
    values = {
        "{python}": sys.executable,
        "{build_out}": str(scratch / "build"),
    }
    return tuple(values.get(item, item) for item in stage.argv)


def _tail(path: Path, limit: int) -> tuple[str, bool]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > limit:
                handle.seek(-limit, os.SEEK_END)
            data = handle.read(limit)
    except OSError:
        return "", False
    return data.decode("utf-8", errors="replace"), size > limit


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def run_stage(stage: Stage, scratch: Path, timeout_seconds: float) -> dict[str, object]:
    stdout_path = scratch / f"{stage.name}.stdout"
    stderr_path = scratch / f"{stage.name}.stderr"
    before_cpu = _child_cpu()
    started = time.monotonic()
    returncode: int | None = None
    timed_out = False
    launch_error: str | None = None

    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            try:
                completed = subprocess.run(
                    expand_argv(stage, scratch),
                    cwd=ROOT,
                    check=False,
                    stdout=stdout,
                    stderr=stderr,
                    shell=False,
                    timeout=timeout_seconds,
                )
                returncode = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
            except OSError as exc:
                launch_error = exc.__class__.__name__
    finally:
        wall_seconds = max(0.0, time.monotonic() - started)

    after_cpu = _child_cpu()
    child_user: float | None = None
    child_system: float | None = None
    if before_cpu is not None and after_cpu is not None:
        child_user = max(0.0, after_cpu[0] - before_cpu[0])
        child_system = max(0.0, after_cpu[1] - before_cpu[1])

    ok = returncode == 0 and not timed_out and launch_error is None
    stdout_tail = ""
    stderr_tail = ""
    truncated = False
    if not ok:
        stdout_tail, stdout_truncated = _tail(stdout_path, MAX_DIAGNOSTIC_BYTES // 2)
        stderr_tail, stderr_truncated = _tail(stderr_path, MAX_DIAGNOSTIC_BYTES // 2)
        truncated = stdout_truncated or stderr_truncated

    return {
        "name": stage.name,
        "command": display_argv(stage),
        "ok": ok,
        "returncode": returncode,
        "timed_out": timed_out,
        "launch_error": launch_error,
        "wall_seconds": round(wall_seconds, 6),
        "child_user_seconds": None if child_user is None else round(child_user, 6),
        "child_system_seconds": None if child_system is None else round(child_system, 6),
        "stdout_bytes": _file_size(stdout_path),
        "stderr_bytes": _file_size(stderr_path),
        "stdout_tail": stdout_tail if not ok else None,
        "stderr_tail": stderr_tail if not ok else None,
        "diagnostics_truncated": truncated,
    }


def summarize(iterations: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for iteration in iterations:
        stages = iteration.get("stages", [])
        if not isinstance(stages, list):
            continue
        for raw_stage in stages:
            if not isinstance(raw_stage, dict):
                continue
            name = raw_stage.get("name")
            if isinstance(name, str):
                grouped.setdefault(name, []).append(raw_stage)

    summary: dict[str, object] = {}
    for name, stages in grouped.items():
        wall = [float(stage["wall_seconds"]) for stage in stages]
        cpu = [
            float(stage["child_user_seconds"]) + float(stage["child_system_seconds"])
            for stage in stages
            if stage.get("child_user_seconds") is not None
            and stage.get("child_system_seconds") is not None
        ]
        summary[name] = {
            "count": len(stages),
            "passed": sum(1 for stage in stages if stage.get("ok") is True),
            "failed": sum(1 for stage in stages if stage.get("ok") is not True),
            "median_wall_seconds": round(statistics.median(wall), 6),
            "min_wall_seconds": round(min(wall), 6),
            "max_wall_seconds": round(max(wall), 6),
            "median_child_cpu_seconds": None
            if not cpu
            else round(statistics.median(cpu), 6),
        }
    return summary


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--profile", choices=sorted(PROFILES), default="core")
    result.add_argument("--repetitions", type=int, default=1)
    result.add_argument("--interval-seconds", type=float, default=0.0)
    result.add_argument("--stage-timeout-seconds", type=float, default=900.0)
    result.add_argument("--scratch-parent", type=Path)
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--json", action="store_true", dest="json_output")
    return result


def validate_arguments(args: argparse.Namespace) -> str | None:
    if not 1 <= args.repetitions <= MAX_REPETITIONS:
        return f"repetitions must be within [1, {MAX_REPETITIONS}]"
    if (
        not math.isfinite(args.interval_seconds)
        or not 0 <= args.interval_seconds <= MAX_INTERVAL_SECONDS
    ):
        return f"interval-seconds must be within [0, {MAX_INTERVAL_SECONDS}]"
    if (
        not math.isfinite(args.stage_timeout_seconds)
        or not 0 < args.stage_timeout_seconds <= MAX_STAGE_TIMEOUT_SECONDS
    ):
        return f"stage-timeout-seconds must be within (0, {MAX_STAGE_TIMEOUT_SECONDS}]"
    if args.scratch_parent is not None and not args.scratch_parent.is_dir():
        return "scratch-parent must be an existing directory"
    return None


def plan(profile: str) -> list[dict[str, object]]:
    return [
        {
            "name": stage.name,
            "command": display_argv(stage),
        }
        for stage in PROFILES[profile]
    ]


def emit(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return
    print(f"profile: {payload['profile']}")
    print(f"ok: {str(payload['ok']).lower()}")
    if payload.get("dry_run"):
        for stage in payload["plan"]:  # type: ignore[index]
            print(f"  {stage['name']}: {' '.join(stage['command'])}")  # type: ignore[index]
        return
    for iteration in payload.get("iterations", []):  # type: ignore[union-attr]
        print(f"iteration {iteration['index']}: ok={str(iteration['ok']).lower()}")
        for stage in iteration["stages"]:
            print(f"  {stage['name']}: {stage['wall_seconds']}s ok={str(stage['ok']).lower()}")


def main() -> int:
    args = parser().parse_args()
    error = validate_arguments(args)
    started_at = utc_now()
    started_clock = time.monotonic()
    base: dict[str, object] = {
        "schema": SCHEMA,
        "profile": args.profile,
        "dry_run": bool(args.dry_run),
        "repetitions_requested": args.repetitions,
        "interval_seconds": args.interval_seconds,
        "stage_timeout_seconds": args.stage_timeout_seconds,
        "source": source_context(),
        "environment": environment_context(),
        "plan": plan(args.profile),
        "started_at": started_at,
    }
    if error is not None:
        base.update(
            {
                "ok": False,
                "error": {"code": "invalid_arguments", "message": error},
                "finished_at": utc_now(),
                "duration_seconds": round(max(0.0, time.monotonic() - started_clock), 6),
                "iterations": [],
                "summary": {},
            }
        )
        emit(base, json_output=args.json_output)
        return 2

    if args.dry_run:
        base.update(
            {
                "ok": True,
                "error": None,
                "finished_at": utc_now(),
                "duration_seconds": round(max(0.0, time.monotonic() - started_clock), 6),
                "iterations": [],
                "summary": {},
            }
        )
        emit(base, json_output=args.json_output)
        return 0

    iterations: list[dict[str, object]] = []
    overall_ok = True
    parent = str(args.scratch_parent) if args.scratch_parent is not None else None
    for index in range(1, args.repetitions + 1):
        iteration_started = utc_now()
        iteration_clock = time.monotonic()
        load_start = _load_average()
        free_start = _free_space_bytes()
        stage_results: list[dict[str, object]] = []
        iteration_ok = True

        with tempfile.TemporaryDirectory(
            prefix="cospaces-external-workload-",
            dir=parent,
        ) as scratch_name:
            scratch = Path(scratch_name)
            for stage in PROFILES[args.profile]:
                result = run_stage(stage, scratch, args.stage_timeout_seconds)
                stage_results.append(result)
                if result["ok"] is not True:
                    iteration_ok = False
                    overall_ok = False
                    break

        iterations.append(
            {
                "index": index,
                "ok": iteration_ok,
                "started_at": iteration_started,
                "finished_at": utc_now(),
                "duration_seconds": round(max(0.0, time.monotonic() - iteration_clock), 6),
                "load_average_start": load_start,
                "load_average_end": _load_average(),
                "free_space_bytes_start": free_start,
                "free_space_bytes_end": _free_space_bytes(),
                "stages": stage_results,
            }
        )
        if not iteration_ok:
            break
        if index < args.repetitions and args.interval_seconds > 0:
            time.sleep(args.interval_seconds)

    failure = None
    if not overall_ok:
        failure = {
            "code": "stage_failed",
            "message": "a required workload stage failed",
        }
    base.update(
        {
            "ok": overall_ok,
            "error": failure,
            "finished_at": utc_now(),
            "duration_seconds": round(max(0.0, time.monotonic() - started_clock), 6),
            "iterations": iterations,
            "summary": summarize(iterations),
        }
    )
    emit(base, json_output=args.json_output)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
