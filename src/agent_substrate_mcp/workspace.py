from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _run_git(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()


def resolve_repo(path: str | None = None) -> Path:
    start = Path(path or ".").expanduser().resolve()
    if start.is_file():
        start = start.parent
    root = _run_git(["rev-parse", "--show-toplevel"], start)
    return Path(root).resolve() if root else start


def discover_repos(root: str, max_depth: int = 4) -> list[dict[str, str]]:
    base = Path(root).expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(f"Root does not exist: {base}")

    repos: list[dict[str, str]] = []
    for git_dir in base.rglob(".git"):
        rel_depth = len(git_dir.relative_to(base).parts)
        if rel_depth > max_depth + 1:
            continue
        repo = git_dir.parent
        repos.append({"name": repo.name, "path": str(repo)})
    return sorted(repos, key=lambda item: item["path"])


def git_status(repo_path: str | None = None) -> dict[str, Any]:
    repo = resolve_repo(repo_path)
    branch = _run_git(["branch", "--show-current"], repo) or ""
    short = _run_git(["status", "--short"], repo) or ""
    return {
        "repo_path": str(repo),
        "branch": branch,
        "dirty": bool(short.strip()),
        "status_short": short.splitlines(),
    }


def read_profile(repo_path: str | None = None) -> dict[str, Any]:
    repo = resolve_repo(repo_path)
    explicit = repo / ".agent-substrate" / "profile.json"
    if explicit.exists():
        with explicit.open("r", encoding="utf-8") as handle:
            profile = json.load(handle)
        profile.setdefault("name", repo.name)
        profile.setdefault("repo_path", str(repo))
        profile.setdefault("checks", [])
        profile.setdefault("conventions", [])
        profile["source"] = str(explicit)
        return profile

    return infer_profile(repo)


def infer_profile(repo: Path) -> dict[str, Any]:
    languages: list[str] = []
    checks: list[dict[str, Any]] = []
    conventions: list[str] = []

    package_json = repo / "package.json"
    if package_json.exists():
        languages.append("javascript")
        with package_json.open("r", encoding="utf-8") as handle:
            package = json.load(handle)
        scripts = package.get("scripts", {})
        package_manager = _detect_node_package_manager(repo)
        runner = _node_runner(package_manager)
        if "test" in scripts:
            checks.append({"id": "test", "label": "Node tests", "command": [*runner, "test"]})
        if "lint" in scripts:
            checks.append({"id": "lint", "label": "Node lint", "command": [*runner, "run", "lint"]})
        if "typecheck" in scripts:
            checks.append({"id": "typecheck", "label": "Node typecheck", "command": [*runner, "run", "typecheck"]})

    if (repo / "pyproject.toml").exists() or (repo / "setup.py").exists():
        languages.append("python")
        checks.append({"id": "pytest", "label": "Python tests", "command": ["pytest"]})

    if (repo / "go.mod").exists():
        languages.append("go")
        checks.append({"id": "go-test", "label": "Go tests", "command": ["go", "test", "./..."]})

    if (repo / "Cargo.toml").exists():
        languages.append("rust")
        checks.append({"id": "cargo-test", "label": "Rust tests", "command": ["cargo", "test"]})

    if not checks:
        conventions.append("No validation checks inferred. Add .agent-substrate/profile.json to make checks explicit.")

    return {
        "name": repo.name,
        "repo_path": str(repo),
        "summary": "",
        "languages": sorted(set(languages)),
        "checks": _dedupe_checks(checks),
        "conventions": conventions,
        "source": "inferred",
    }


def workspace_context(repo_path: str | None = None) -> dict[str, Any]:
    profile = read_profile(repo_path)
    status = git_status(profile["repo_path"])
    return {
        "repo": {
            "name": profile["name"],
            "path": profile["repo_path"],
            "summary": profile.get("summary", ""),
            "languages": profile.get("languages", []),
            "profile_source": profile.get("source", ""),
        },
        "checks": profile.get("checks", []),
        "conventions": profile.get("conventions", []),
        "git": status,
    }


def _detect_node_package_manager(repo: Path) -> str:
    if (repo / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _node_runner(package_manager: str) -> list[str]:
    if package_manager == "pnpm":
        return ["corepack", "pnpm"]
    if package_manager == "yarn":
        return ["corepack", "yarn"]
    return ["npm"]


def _dedupe_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for check in checks:
        if check["id"] in seen:
            continue
        seen.add(check["id"])
        result.append(check)
    return result

