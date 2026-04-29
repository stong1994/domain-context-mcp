import json
import sys

import pytest

from domain_context_mcp.execution import run_check
from domain_context_mcp.store import JsonStore
from domain_context_mcp.tasks import begin_task, complete_task


def test_run_check_records_named_profile_check(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    profile_dir = repo / ".domain-context"
    profile_dir.mkdir(parents=True)
    profile = {
        "name": "demo",
        "checks": [
            {
                "id": "smoke",
                "label": "Smoke check",
                "command": [sys.executable, "-c", "print('ok')"],
            }
        ],
    }
    (profile_dir / "profile.json").write_text(json.dumps(profile), encoding="utf-8")

    started = begin_task(store, "run smoke", str(repo))
    record = run_check(store, started["task"]["id"], "smoke", str(repo))
    completed = complete_task(store, started["task"]["id"])

    assert record["exit_code"] == 0
    assert record["stdout_tail"].strip() == "ok"
    assert completed["task"]["status"] == "completed"


def test_run_check_rejects_unknown_check(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    profile_dir = repo / ".domain-context"
    profile_dir.mkdir(parents=True)
    (profile_dir / "profile.json").write_text(
        json.dumps({"name": "demo", "checks": []}),
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        run_check(store, "t_missing", "not-profiled", str(repo))

