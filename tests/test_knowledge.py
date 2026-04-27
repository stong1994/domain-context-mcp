from agent_substrate_mcp.knowledge import decide_knowledge, propose_knowledge, search_knowledge
from agent_substrate_mcp.store import JsonStore


def test_knowledge_requires_acceptance_before_search(tmp_path):
    store = JsonStore(tmp_path)
    proposed = propose_knowledge(
        store,
        kind="repo_convention",
        scope="repo:/tmp/example",
        title="Use named checks",
        body="Validation commands should be profile checks.",
        tags=["validation"],
    )

    assert search_knowledge(store, "validation") == []

    accepted = decide_knowledge(store, proposed["id"], "accept", "Looks durable.")

    assert accepted["status"] == "accepted"
    assert [item["id"] for item in search_knowledge(store, "validation")] == [proposed["id"]]


def test_rejected_knowledge_is_not_active(tmp_path):
    store = JsonStore(tmp_path)
    proposed = propose_knowledge(
        store,
        kind="preference",
        scope="user",
        title="Temporary note",
        body="This should not become active.",
    )

    rejected = decide_knowledge(store, proposed["id"], "reject", "Too situational.")

    assert rejected["status"] == "rejected"
    assert search_knowledge(store, "temporary") == []

