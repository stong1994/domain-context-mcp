import subprocess

from agent_substrate_mcp.knowledge import decide_knowledge, propose_knowledge
from agent_substrate_mcp.store import JsonStore
from agent_substrate_mcp.tasks import begin_task, complete_task


def test_task_complete_warns_without_execution(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()

    started = begin_task(store, "make a change", str(repo))
    completed = complete_task(store, started["task"]["id"])

    assert completed["task"]["status"] == "completed_with_warnings"
    assert "No execution checks recorded for this task." in completed["warnings"]


def test_task_complete_warns_on_pending_knowledge(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()

    started = begin_task(store, "make a change", str(repo))
    proposal = propose_knowledge(
        store,
        kind="repo_convention",
        scope=f"repo:{repo}",
        title="Remember something",
        body="Pending review.",
        source_task_id=started["task"]["id"],
    )

    completed = complete_task(store, started["task"]["id"])
    assert "knowledge proposal(s) still need review" in " ".join(completed["warnings"])

    decide_knowledge(store, proposal["id"], "accept")


def test_task_begin_reuses_active_task_with_idempotency_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()

    first = begin_task(store, "make a change", str(repo), idempotency_key="same")
    second = begin_task(store, "make a change again", str(repo), idempotency_key="same")

    assert first["created"] is True
    assert second["created"] is False
    assert first["task"]["id"] == second["task"]["id"]


def test_task_current_matches_repo_subdirectory(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    child = repo / "src"
    child.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    first = begin_task(store, "make a change", str(repo), idempotency_key="same")
    current = begin_task(store, "make a change", str(child), idempotency_key="same")

    assert current["created"] is False
    assert first["task"]["id"] == current["task"]["id"]
