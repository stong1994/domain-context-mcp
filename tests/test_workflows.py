import json
import sys

from agent_substrate_mcp.domains import create_domain, read_domain
from agent_substrate_mcp.store import JsonStore
from agent_substrate_mcp.workflows import (
    learning_review,
    work_begin,
    work_checkpoint,
    work_finish,
)


def write_profile(repo, checks=None):
    profile_dir = repo / ".agent-substrate"
    profile_dir.mkdir(parents=True)
    profile = {
        "name": "demo",
        "languages": ["python"],
        "checks": checks
        or [
            {
                "id": "smoke",
                "label": "Smoke",
                "command": [sys.executable, "-c", "print('ok')"],
            }
        ],
    }
    (profile_dir / "profile.json").write_text(json.dumps(profile), encoding="utf-8")


def test_work_begin_returns_task_domain_knowledge_and_checks(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    write_profile(repo)
    domain = create_domain(store, "Python MCP Server", "Working on Python MCP servers.", repos=[str(repo)])

    result = work_begin(
        store,
        user_request="Improve smoke workflow",
        repo_path=str(repo),
        domain_hint=domain["domain"]["id"],
        idempotency_key="same",
    )
    reused = work_begin(
        store,
        user_request="Improve smoke workflow again",
        repo_path=str(repo),
        domain_hint=domain["domain"]["id"],
        idempotency_key="same",
    )

    assert result["created"] is True
    assert reused["created"] is False
    assert result["task"]["domain_ids"] == [domain["domain"]["id"]]
    assert result["suggested_checks"][0]["id"] == "smoke"
    assert result["domain_context"][0]["domain"]["id"] == domain["domain"]["id"]


def test_work_checkpoint_runs_checks_and_proposes_updates(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    write_profile(repo)
    domain = create_domain(store, "Python MCP Server", "Working on Python MCP servers.", repos=[str(repo)])
    started = work_begin(store, "Improve smoke workflow", str(repo), domain_hint=domain["domain"]["id"])

    result = work_checkpoint(
        store,
        task_id=started["task"]["id"],
        summary="Found a durable convention.",
        repo_path=str(repo),
        run_check_ids=["smoke"],
        knowledge_updates=[
            {
                "domain_id": domain["domain"]["id"],
                "proposal": {
                    "title": "Run smoke checks",
                    "body": "Run the smoke check before finishing workflow changes.",
                },
                "tags": ["smoke"],
            }
        ],
    )

    assert result["checkpoint"]["summary"] == "Found a durable convention."
    assert result["executions"][0]["exit_code"] == 0
    assert result["proposed_updates"][0]["status"] == "proposed"


def test_learning_review_and_work_finish_gate_pending_updates(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    write_profile(repo)
    domain = create_domain(store, "Python MCP Server", "Working on Python MCP servers.", repos=[str(repo)])
    started = work_begin(store, "Improve smoke workflow", str(repo), domain_hint=domain["domain"]["id"])
    checkpoint = work_checkpoint(
        store,
        task_id=started["task"]["id"],
        summary="Proposed a convention.",
        repo_path=str(repo),
        knowledge_updates=[
            {
                "domain_id": domain["domain"]["id"],
                "proposal": {
                    "title": "Run smoke checks",
                    "body": "Run the smoke check before finishing workflow changes.",
                },
            }
        ],
    )

    blocked = work_finish(
        store,
        task_id=started["task"]["id"],
        summary="Finishing before review.",
        repo_path=str(repo),
        run_check_ids=["smoke"],
    )
    reviewed = learning_review(
        store,
        decisions=[
            {
                "update_id": checkpoint["proposed_updates"][0]["id"],
                "decision": "accept",
                "reason": "Durable and verified.",
            }
        ],
    )
    domain_after = read_domain(store, domain["domain"]["id"])

    assert blocked["ready"] is False
    assert blocked["pending_updates"]
    assert reviewed["accepted"][0]["status"] == "accepted"
    assert "Run smoke checks" in domain_after["skill_md"]


def test_work_finish_not_ready_without_validation(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    write_profile(repo)
    domain = create_domain(store, "Python MCP Server", "Working on Python MCP servers.", repos=[str(repo)])
    started = work_begin(store, "Improve smoke workflow", str(repo), domain_hint=domain["domain"]["id"])

    finished = work_finish(
        store,
        task_id=started["task"]["id"],
        summary="Finishing without checks.",
        repo_path=str(repo),
    )

    assert finished["ready"] is False
    assert "No execution checks recorded for this task." in finished["warnings"]
