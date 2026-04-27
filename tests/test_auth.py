from repo_context_mcp import auth


def test_save_status_and_logout_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_CONTEXT_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("REPO_CONTEXT_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert auth.status()["usable"] is False
    path = auth.save_api_key("sk-test123")

    assert path.exists()
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert auth.read_saved_api_key() == "sk-test123"
    assert auth.resolve_openai_api_key() == "sk-test123"
    assert auth.status()["usable"] is True
    assert auth.logout() is True
    assert auth.status()["usable"] is False


def test_env_key_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_CONTEXT_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    auth.save_api_key("sk-saved")

    assert auth.resolve_openai_api_key() == "sk-env"


def test_repo_context_env_key_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_CONTEXT_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    monkeypatch.setenv("REPO_CONTEXT_OPENAI_API_KEY", "sk-agent")
    auth.save_api_key("sk-saved")

    assert auth.resolve_openai_api_key() == "sk-agent"


def test_legacy_openai_env_key_still_works_during_migration(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_CONTEXT_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("REPO_CONTEXT_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_SUBSTRATE_OPENAI_API_KEY", "sk-legacy")

    assert auth.resolve_openai_api_key() == "sk-legacy"
    assert auth.status()["env_source"] == "AGENT_SUBSTRATE_OPENAI_API_KEY"
