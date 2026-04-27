from repo_context_mcp.domains import (
    create_domain,
    duplicate_domain_groups,
    link_domain_repo,
    list_domains,
    merge_domains,
    read_domain,
    rename_domain_directory,
    resolve_domains,
)
import repo_context_mcp.llm as llm
from repo_context_mcp.store import JsonStore


def test_create_domain_writes_skill_and_metadata(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()

    created = create_domain(
        store,
        name="Python MCP Server",
        description="Working on Python MCP servers.",
        repos=[str(repo)],
        tags=["python", "mcp"],
    )

    domain = read_domain(store, created["domain"]["id"])

    assert created["created"] is True
    assert created["domain"]["id"] == "python-mcp-server"
    assert created["domain"]["directory_name_source"] == "deterministic"
    assert domain["domain"]["repos"] == [str(repo.resolve())]
    assert "Working on Python MCP servers" in domain["skill_md"]
    assert (store.root / "domains" / created["domain"]["id"] / "SKILL.md").exists()
    assert (store.root / "domains" / created["domain"]["id"] / "domain.json").exists()


def test_create_domain_reuses_existing_name(tmp_path):
    store = JsonStore(tmp_path / "state")

    first = create_domain(store, "Python MCP Server", "Working on Python MCP servers.")
    second = create_domain(store, "Python MCP Server", "Updated description.")

    assert first["created"] is True
    assert second["created"] is False
    assert first["domain"]["id"] == second["domain"]["id"]


def test_create_domain_uses_llm_generated_readable_directory_name(tmp_path, monkeypatch):
    store = JsonStore(tmp_path / "state")

    def fake_generate_domain_directory_name_with_openai(**kwargs):
        return "mcp-tool-lifecycle"

    monkeypatch.setenv("REPO_CONTEXT_DOMAIN_NAMING", "llm")
    monkeypatch.setattr(llm, "generate_domain_directory_name_with_openai", fake_generate_domain_directory_name_with_openai)

    created = create_domain(store, "Python MCP Server", "Working on Python MCP servers.")

    assert created["created"] is True
    assert created["domain"]["id"] == "mcp-tool-lifecycle"
    assert created["domain"]["directory_name_source"] == "llm"
    assert (store.root / "domains" / "mcp-tool-lifecycle" / "SKILL.md").exists()


def test_link_domain_repo(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    created = create_domain(store, "Repo Domain", "Repo knowledge")

    linked = link_domain_repo(store, created["domain"]["id"], str(repo))

    assert str(repo.resolve()) in linked["repos"]
    assert list_domains(store, repo_path=str(repo.resolve()))[0]["id"] == created["domain"]["id"]


def test_duplicate_domain_groups_recommends_canonical_target(tmp_path):
    store = JsonStore(tmp_path / "state")
    create_domain(store, "Python MCP Server", "Working on Python MCP servers.", domain_id="d_python-mcp-server")
    create_domain(store, "Python MCP Server", "Duplicate domain.", domain_id="d_python-mcp-server_ab12cd")
    create_domain(store, "Other Domain", "Unrelated.")

    groups = duplicate_domain_groups(store)

    assert len(groups) == 1
    assert groups[0]["recommended_target_id"] == "d_python-mcp-server"
    assert {item["id"] for item in groups[0]["domains"]} == {
        "d_python-mcp-server",
        "d_python-mcp-server_ab12cd",
    }


def test_merge_domains_marks_sources_and_remaps_references(tmp_path):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    target = create_domain(
        store,
        "Python MCP Server",
        "Working on Python MCP servers.",
        repos=[str(repo)],
        tags=["python"],
        domain_id="d_python-mcp-server",
    )
    source = create_domain(
        store,
        "Python MCP Server",
        "Duplicate domain.",
        tags=["mcp"],
        body="# Duplicate\n\nKeep this detail.",
        domain_id="d_python-mcp-server_ab12cd",
    )
    target_id = target["domain"]["id"]
    source_id = source["domain"]["id"]
    store.write_collection(
        "tasks",
        [
            {
                "id": "t_1",
                "status": "active",
                "repo_path": str(repo.resolve()),
                "domain_ids": [source_id, target_id],
            }
        ],
    )
    store.write_collection("knowledge", [{"id": "k_1", "domain_id": source_id}])
    store.write_collection("knowledge_updates", [{"id": "ku_1", "domain_id": source_id}])

    result = merge_domains(store, target_id, [source_id], reason="same name")

    assert result["target"]["id"] == target_id
    assert result["sources"][0]["status"] == "merged"
    assert result["sources"][0]["merged_into"] == target_id
    assert result["remapped"] == {"tasks": 1, "knowledge": 1, "knowledge_updates": 1}
    assert store.read_collection("tasks")[0]["domain_ids"] == [target_id]
    assert store.read_collection("knowledge")[0]["domain_id"] == target_id
    assert store.read_collection("knowledge_updates")[0]["domain_id"] == target_id
    assert read_domain(store, source_id)["domain"]["status"] == "merged"
    assert "Merged Domain: Python MCP Server" in read_domain(store, target_id)["skill_md"]
    assert "Keep this detail." in read_domain(store, target_id)["skill_md"]
    assert [item["id"] for item in list_domains(store)] == [target_id]


def test_rename_domain_directory_remaps_references(tmp_path):
    store = JsonStore(tmp_path / "state")
    create_domain(
        store,
        "Python MCP Server",
        "Working on Python MCP servers.",
        domain_id="d_python-mcp-server",
    )
    store.write_collection("tasks", [{"id": "t_1", "domain_ids": ["d_python-mcp-server"]}])
    store.write_collection("knowledge", [{"id": "k_1", "domain_id": "d_python-mcp-server"}])
    store.write_collection("knowledge_updates", [{"id": "ku_1", "domain_id": "d_python-mcp-server"}])

    result = rename_domain_directory(store, "d_python-mcp-server", use_llm=False)

    assert result["renamed"] is True
    assert result["old_domain_id"] == "d_python-mcp-server"
    assert result["new_domain_id"] == "python-mcp-server"
    assert result["domain"]["previous_ids"] == ["d_python-mcp-server"]
    assert not (store.root / "domains" / "d_python-mcp-server").exists()
    assert (store.root / "domains" / "python-mcp-server").exists()
    assert store.read_collection("tasks")[0]["domain_ids"] == ["python-mcp-server"]
    assert store.read_collection("knowledge")[0]["domain_id"] == "python-mcp-server"
    assert store.read_collection("knowledge_updates")[0]["domain_id"] == "python-mcp-server"
    resolved = resolve_domains(store, "Work on Python MCP server", domain_hint="d_python-mcp-server", use_llm=False)
    assert resolved["matched_domains"][0]["domain_id"] == "python-mcp-server"


def test_resolve_domains_falls_back_to_repo_match_without_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    created = create_domain(
        store,
        "Python MCP Server",
        "Working on Python MCP servers.",
        repos=[str(repo)],
        tags=["python", "mcp"],
    )

    result = resolve_domains(store, "Add domain resolution", str(repo), use_llm=True)

    assert result["llm_used"] is False
    assert result["matched_domains"][0]["domain_id"] == created["domain"]["id"]
    assert result["warnings"]


def test_resolve_domains_uses_llm_result_when_available(tmp_path, monkeypatch):
    store = JsonStore(tmp_path / "state")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    created = create_domain(store, "Python MCP Server", "Working on Python MCP servers.", repos=[str(repo)])

    def fake_resolve_domain_with_openai(**kwargs):
        return {
            "llm_used": True,
            "matched_domains": [
                {
                    "domain_id": created["domain"]["id"],
                    "confidence": 0.92,
                    "reason": "Semantic match.",
                    "matched_by": ["llm"],
                }
            ],
            "new_domain_needed": False,
            "suggested_domain": None,
            "warnings": [],
        }

    monkeypatch.setattr(llm, "resolve_domain_with_openai", fake_resolve_domain_with_openai)

    result = resolve_domains(store, "Improve the MCP tool lifecycle", str(repo), use_llm=True)

    assert result["llm_used"] is True
    assert result["matched_domains"][0]["matched_by"] == ["llm"]
