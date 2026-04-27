from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from .store import JsonStore, now_iso

AUTH_FILE = "auth.json"


def auth_path() -> Path:
    return JsonStore.from_env().root / AUTH_FILE


def read_saved_api_key() -> str | None:
    path = auth_path()
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    key = data.get("openai_api_key")
    return key if isinstance(key, str) and key else None


def resolve_openai_api_key() -> str | None:
    return (
        os.environ.get("REPO_CONTEXT_OPENAI_API_KEY")
        or os.environ.get("AGENT_SUBSTRATE_OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or read_saved_api_key()
    )


def save_api_key(api_key: str) -> Path:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API key is empty")
    if not api_key.startswith(("sk-", "sess-")):
        raise ValueError("API key does not look like an OpenAI API key")

    path = auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "openai_api_key": api_key,
        "created_at": now_iso(),
    }
    fd, tmp_name = tempfile.mkstemp(prefix=".auth.", suffix=".json", dir=path.parent)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()
    return path


def logout() -> bool:
    path = auth_path()
    if path.exists():
        path.unlink()
        return True
    return False


def status() -> dict[str, Any]:
    path = auth_path()
    env_source = None
    if os.environ.get("REPO_CONTEXT_OPENAI_API_KEY"):
        env_source = "REPO_CONTEXT_OPENAI_API_KEY"
    elif os.environ.get("AGENT_SUBSTRATE_OPENAI_API_KEY"):
        env_source = "AGENT_SUBSTRATE_OPENAI_API_KEY"
    elif os.environ.get("OPENAI_API_KEY"):
        env_source = "OPENAI_API_KEY"
    return {
        "env_source": env_source,
        "saved_auth_path": str(path),
        "saved_auth_exists": path.exists(),
        "usable": bool(resolve_openai_api_key()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-context-auth")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Store OpenAI API credentials")
    login_parser.add_argument(
        "--with-api-key",
        action="store_true",
        help="Read the OpenAI API key from stdin",
    )

    subparsers.add_parser("status", help="Show credential status without revealing secrets")
    subparsers.add_parser("logout", help="Remove saved credentials")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "login":
        if not args.with_api_key:
            parser.error("login currently requires --with-api-key")
        api_key = sys.stdin.read().strip()
        path = save_api_key(api_key)
        print(f"Saved OpenAI API key to {path}")
        return 0

    if args.command == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "logout":
        removed = logout()
        print("Removed saved credentials" if removed else "No saved credentials found")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
