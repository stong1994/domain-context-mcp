from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_COMMAND = PROJECT_ROOT / ".venv" / "bin" / "domain-context-mcp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dogfood the Domain Context MCP server over stdio.")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="Ledger directory. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository path to use for workspace context and checks.",
    )
    return parser.parse_args()


async def call(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise RuntimeError(f"{name} failed: {result.content}")
    if result.structuredContent and "result" in result.structuredContent:
        return result.structuredContent["result"]
    if not result.content:
        return None
    item = result.content[0]
    if item.type != "text":
        return item
    return json.loads(item.text)


async def run_dogfood(state_dir: Path, repo_path: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["DOMAIN_CONTEXT_HOME"] = str(state_dir)

    params = StdioServerParameters(
        command=str(SERVER_COMMAND),
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools_result.tools)

            domain = await call(
                session,
                "domain_create",
                {
                    "name": "Python MCP Server",
                    "description": "working on local Python MCP servers, stdio transports, tool schemas, task ledgers, and domain knowledge lifecycle flows",
                    "repos": [str(repo_path)],
                    "tags": ["python", "mcp", "domain-context"],
                },
            )
            domain_id = domain["domain"]["id"]
            started = await call(
                session,
                "work_begin",
                {
                    "user_request": "Dogfood the workflow-oriented MCP lifecycle through a real stdio MCP client.",
                    "repo_path": str(repo_path),
                    "domain_hint": domain_id,
                    "idempotency_key": "dogfood-workflow-lifecycle",
                },
            )
            task_id = started["task"]["id"]

            context = started["workspace_context"]
            checks = started["suggested_checks"]
            check_id = checks[0]["id"]
            checkpoint = await call(
                session,
                "work_checkpoint",
                {
                    "task_id": task_id,
                    "repo_path": str(repo_path),
                    "summary": "Verified workflow checkpoint can run checks and propose domain knowledge updates.",
                    "run_check_ids": [check_id],
                    "knowledge_updates": [
                        {
                            "domain_id": domain_id,
                            "operation": "create",
                            "proposal": {
                                "kind": "repo_convention",
                                "scope": f"repo:{repo_path}",
                                "title": "Dogfood workflow tools before client rollout",
                                "body": "Use scripts/dogfood_mcp.py to verify work_begin, work_checkpoint, learning_review, and work_finish before wiring this server into a daily client.",
                            },
                            "tags": ["mcp", "dogfood", "workflow"],
                        }
                    ],
                    "timeout_seconds": 120,
                },
            )
            update = checkpoint["proposed_updates"][0]
            review = await call(
                session,
                "learning_review",
                {
                    "decisions": [
                        {
                            "update_id": update["id"],
                            "decision": "accept",
                            "reason": "The workflow flow was verified through the MCP client.",
                        }
                    ]
                },
            )
            accepted = review["accepted"][0]
            completed = await call(
                session,
                "work_finish",
                {
                    "task_id": task_id,
                    "summary": "Completed workflow-oriented dogfood.",
                    "repo_path": str(repo_path),
                    "run_check_ids": [check_id],
                },
            )

            return {
                "server": "domain-context",
                "tool_count": len(tool_names),
                "tools": tool_names,
                "state_dir": str(state_dir),
                "repo": context["repo"],
                "domain_id": domain_id,
                "domain_resolution": started["domain_resolution"],
                "task_id": task_id,
                "task_created": started["created"],
                "check_id": check_id,
                "checkpoint_execution_exit_code": checkpoint["executions"][0]["exit_code"],
                "finish_execution_exit_code": completed["executions"][0]["exit_code"],
                "knowledge_update_id": accepted["id"],
                "knowledge_id": accepted["resulting_knowledge_id"],
                "task_status": completed["task"]["status"],
                "ready": completed["ready"],
                "warnings": completed["warnings"],
            }


async def main_async() -> int:
    args = parse_args()
    if not SERVER_COMMAND.exists():
        print(f"Server command not found: {SERVER_COMMAND}", file=sys.stderr)
        return 1

    if args.state_dir is None:
        with tempfile.TemporaryDirectory(prefix="domain-context-dogfood-") as tmp:
            summary = await run_dogfood(Path(tmp), args.repo_path.resolve())
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

    args.state_dir.mkdir(parents=True, exist_ok=True)
    summary = await run_dogfood(args.state_dir.resolve(), args.repo_path.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
