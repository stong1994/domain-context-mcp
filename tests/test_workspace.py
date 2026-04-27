import json

from agent_substrate_mcp.workspace import read_profile, workspace_context


def test_explicit_profile_is_used(tmp_path):
    repo = tmp_path / "repo"
    profile_dir = repo / ".agent-substrate"
    profile_dir.mkdir(parents=True)
    profile = {
        "name": "demo",
        "languages": ["python"],
        "checks": [{"id": "tests", "label": "Tests", "command": ["pytest"]}],
        "conventions": ["Keep tools high-level."],
    }
    (profile_dir / "profile.json").write_text(json.dumps(profile), encoding="utf-8")

    loaded = read_profile(str(repo))

    assert loaded["name"] == "demo"
    assert loaded["checks"][0]["id"] == "tests"
    assert loaded["source"].endswith(".agent-substrate/profile.json")


def test_infers_python_profile(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    context = workspace_context(str(repo))

    assert "python" in context["repo"]["languages"]
    assert context["checks"][0]["id"] == "pytest"

