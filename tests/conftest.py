import pytest


@pytest.fixture(autouse=True)
def deterministic_domain_naming(monkeypatch):
    monkeypatch.setenv("REPO_CONTEXT_DOMAIN_NAMING", "deterministic")
