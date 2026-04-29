from __future__ import annotations

import subprocess
import time
from typing import Any
from uuid import uuid4

from .store import JsonStore, now_iso, tail
from .workspace import read_profile, resolve_repo

COLLECTION = "executions"


def suggest_checks(repo_path: str | None = None) -> list[dict[str, Any]]:
    profile = read_profile(repo_path)
    return profile.get("checks", [])


def run_check(
    store: JsonStore,
    task_id: str,
    check_id: str,
    repo_path: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    repo = resolve_repo(repo_path)
    profile = read_profile(str(repo))
    check = _find_check(profile.get("checks", []), check_id)
    start = time.monotonic()
    started_at = now_iso()

    try:
        result = subprocess.run(
            check["command"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timed_out = True
    except OSError as exc:
        exit_code = 127
        stdout = ""
        stderr = str(exc)
        timed_out = False

    duration_ms = int((time.monotonic() - start) * 1000)
    record = {
        "id": f"e_{uuid4().hex[:12]}",
        "task_id": task_id,
        "repo_path": str(repo),
        "check_id": check_id,
        "label": check.get("label", check_id),
        "command": check["command"],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "started_at": started_at,
        "completed_at": now_iso(),
        "stdout_tail": tail(stdout),
        "stderr_tail": tail(stderr),
    }
    return store.append(COLLECTION, record)


def _find_check(checks: list[dict[str, Any]], check_id: str) -> dict[str, Any]:
    for check in checks:
        if check.get("id") == check_id:
            command = check.get("command")
            if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
                raise ValueError(f"Check {check_id} must define command as a non-empty string list")
            return check
    raise KeyError(f"Unknown check id: {check_id}")

