from agent_substrate_mcp.domains import create_domain, read_domain
from agent_substrate_mcp.knowledge import (
    decide_knowledge_update,
    propose_knowledge_update,
    search_knowledge,
)
from agent_substrate_mcp.store import JsonStore
from agent_substrate_mcp.tasks import begin_task, complete_task


def test_accept_knowledge_update_writes_domain_skill(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    domain = create_domain(store, "Python MCP Server", "Working on Python MCP servers.", repos=[str(repo)])
    task = begin_task(store, "record convention", str(repo))["task"]
    update = propose_knowledge_update(
        store,
        domain_id=domain["domain"]["id"],
        source_task_id=task["id"],
        operation="create",
        proposal={
            "kind": "convention",
            "title": "Run dogfood before client rollout",
            "body": "Run scripts/dogfood_mcp.py before changing client-facing MCP tools.",
        },
        tags=["dogfood"],
    )

    completed_before = complete_task(store, task["id"])
    accepted = decide_knowledge_update(store, update["id"], "accept", "Verified.")
    domain_after = read_domain(store, domain["domain"]["id"])
    results = search_knowledge(store, "dogfood", domain_id=domain["domain"]["id"])

    assert completed_before["task"]["status"] == "completed_with_warnings"
    assert accepted["status"] == "accepted"
    assert accepted["resulting_knowledge_id"]
    assert "Run dogfood before client rollout" in domain_after["skill_md"]
    assert any(item["kind"] == "domain_skill" for item in results)

