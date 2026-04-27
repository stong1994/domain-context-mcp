import pytest


@pytest.fixture(autouse=True)
def deterministic_domain_naming(monkeypatch):
    monkeypatch.setenv("AGENT_SUBSTRATE_DOMAIN_NAMING", "deterministic")
