from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .domains import (
    create_domain,
    domain_context as build_domain_context,
    duplicate_domain_groups,
    link_domain_repo,
    list_domains,
    merge_domains,
    read_domain,
    rename_domain_directory,
    resolve_domains,
)
from .execution import run_check, suggest_checks
from .knowledge import (
    decide_knowledge,
    decide_knowledge_update,
    list_knowledge,
    list_knowledge_updates,
    propose_knowledge,
    propose_knowledge_update,
    read_knowledge,
    read_knowledge_update,
    search_knowledge,
)
from .store import JsonStore
from .tasks import begin_task, complete_task, find_current_task, list_tasks, resume_task
from .workflows import (
    learning_review as run_learning_review,
    work_begin as run_work_begin,
    work_checkpoint as run_work_checkpoint,
    work_finish as run_work_finish,
)
from .workspace import discover_repos, workspace_context as build_workspace_context

mcp = FastMCP("repo-context")
STORE = JsonStore.from_env()


@mcp.tool()
def work_begin(
    user_request: str,
    repo_path: str | None = None,
    conversation_id: str | None = None,
    idempotency_key: str | None = None,
    domain_hint: str | None = None,
    knowledge_query: str | None = None,
    knowledge_limit: int = 5,
) -> dict[str, Any]:
    """Start repo work with task, workspace, domain, knowledge, and check context."""
    return run_work_begin(
        STORE,
        user_request=user_request,
        repo_path=repo_path,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
        domain_hint=domain_hint,
        knowledge_query=knowledge_query,
        knowledge_limit=knowledge_limit,
    )


@mcp.tool()
def work_checkpoint(
    task_id: str,
    summary: str,
    repo_path: str | None = None,
    run_check_ids: list[str] | None = None,
    knowledge_updates: list[dict[str, Any]] | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Record progress, optionally run named checks and propose domain knowledge updates."""
    return run_work_checkpoint(
        STORE,
        task_id=task_id,
        summary=summary,
        repo_path=repo_path,
        run_check_ids=run_check_ids,
        knowledge_updates=knowledge_updates,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def work_finish(
    task_id: str,
    summary: str,
    repo_path: str | None = None,
    run_check_ids: list[str] | None = None,
    require_clean: bool = False,
    allow_pending_updates: bool = False,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Finish repo work with final checks, task completion, and readiness reporting."""
    return run_work_finish(
        STORE,
        task_id=task_id,
        summary=summary,
        repo_path=repo_path,
        run_check_ids=run_check_ids,
        require_clean=require_clean,
        allow_pending_updates=allow_pending_updates,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def learning_review(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Accept or reject proposed domain knowledge updates in one batch."""
    return run_learning_review(STORE, decisions=decisions)


@mcp.tool()
def task_begin(
    user_request: str,
    repo_path: str | None = None,
    domain_hint: str | None = None,
    conversation_id: str | None = None,
    idempotency_key: str | None = None,
    resolve_domain_context: bool = True,
) -> dict[str, Any]:
    """Open a task ledger entry and return initial workspace context."""
    return begin_task(
        STORE,
        user_request=user_request,
        repo_path=repo_path,
        domain_hint=domain_hint,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
        resolve_domain_context=resolve_domain_context,
    )


@mcp.tool()
def task_complete(task_id: str) -> dict[str, Any]:
    """Close a task and report missing validation or pending learning review."""
    return complete_task(STORE, task_id=task_id)


@mcp.tool()
def task_list(
    status: str | None = None,
    repo_path: str | None = None,
    conversation_id: str | None = None,
) -> list[dict[str, Any]]:
    """List task ledger entries."""
    return list_tasks(STORE, status=status, repo_path=repo_path, conversation_id=conversation_id)


@mcp.tool()
def task_current(
    repo_path: str | None = None,
    conversation_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    """Return the active task matching repo, conversation, or idempotency key."""
    return find_current_task(
        STORE,
        repo_path=repo_path,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
    )


@mcp.tool()
def task_resume(task_id: str) -> dict[str, Any]:
    """Resume a task by marking it active."""
    return resume_task(STORE, task_id=task_id)


@mcp.tool()
def workspace_discover(root: str, max_depth: int = 4) -> list[dict[str, str]]:
    """Find git repositories under a root path."""
    return discover_repos(root=root, max_depth=max_depth)


@mcp.tool()
def workspace_context(repo_path: str | None = None) -> dict[str, Any]:
    """Return repo profile, git state, conventions, and suggested checks."""
    return build_workspace_context(repo_path=repo_path)


@mcp.tool()
def domain_list(
    status: str | None = "active",
    repo_path: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    """List skill-like knowledge domains."""
    return list_domains(STORE, status=status, repo_path=repo_path, tag=tag)


@mcp.tool()
def domain_read(domain_id: str) -> dict[str, Any]:
    """Read a domain's metadata and SKILL.md body."""
    return read_domain(STORE, domain_id=domain_id)


@mcp.tool()
def domain_duplicate_groups(
    status: str | None = "active",
    repo_path: str | None = None,
) -> list[dict[str, Any]]:
    """Find duplicate domain groups by normalized domain name."""
    return duplicate_domain_groups(STORE, status=status, repo_path=repo_path)


@mcp.tool()
def domain_create(
    name: str,
    description: str,
    repos: list[str] | None = None,
    tags: list[str] | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    """Create a skill-like domain backed by SKILL.md and domain.json."""
    return create_domain(
        STORE,
        name=name,
        description=description,
        repos=repos,
        tags=tags,
        body=body,
    )


@mcp.tool()
def domain_merge(
    target_domain_id: str,
    source_domain_ids: list[str],
    reason: str | None = None,
) -> dict[str, Any]:
    """Merge source domains into a target and remap task/knowledge references."""
    return merge_domains(
        STORE,
        target_domain_id=target_domain_id,
        source_domain_ids=source_domain_ids,
        reason=reason,
    )


@mcp.tool()
def domain_rename_directory(
    domain_id: str,
    new_domain_id: str | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Rename a domain directory and remap task/knowledge references."""
    return rename_domain_directory(
        STORE,
        domain_id=domain_id,
        new_domain_id=new_domain_id,
        use_llm=use_llm,
    )


@mcp.tool()
def domain_link_repo(domain_id: str, repo_path: str) -> dict[str, Any]:
    """Link a repository to a domain."""
    return link_domain_repo(STORE, domain_id=domain_id, repo_path=repo_path)


@mcp.tool()
def domain_context(domain_ids: list[str]) -> list[dict[str, Any]]:
    """Return SKILL.md context for one or more domains."""
    return build_domain_context(STORE, domain_ids=domain_ids)


@mcp.tool()
def domain_resolve(
    user_request: str,
    repo_path: str | None = None,
    domain_hint: str | None = None,
    use_llm: bool = True,
    create_if_missing: bool = False,
) -> dict[str, Any]:
    """Resolve which skill-like domains apply to a task, using OpenAI API when configured."""
    return resolve_domains(
        STORE,
        user_request=user_request,
        repo_path=repo_path,
        domain_hint=domain_hint,
        use_llm=use_llm,
        create_if_missing=create_if_missing,
    )


@mcp.tool()
def knowledge_list(status: str | None = None, scope: str | None = None) -> list[dict[str, Any]]:
    """List knowledge ledger entries, optionally filtered by status or scope."""
    return list_knowledge(STORE, status=status, scope=scope)


@mcp.tool()
def knowledge_read(knowledge_id: str) -> dict[str, Any]:
    """Read one knowledge ledger entry."""
    return read_knowledge(STORE, knowledge_id=knowledge_id)


@mcp.tool()
def knowledge_search(
    query: str,
    scope: str | None = None,
    domain_id: str | None = None,
    status: str = "active",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search reviewed knowledge for relevant conventions and memories."""
    return search_knowledge(
        STORE,
        query=query,
        scope=scope,
        domain_id=domain_id,
        status=status,
        limit=limit,
    )


@mcp.tool()
def knowledge_propose(
    kind: str,
    scope: str,
    title: str,
    body: str,
    source_task_id: str | None = None,
    domain_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a proposed learning. Proposed entries are not active until accepted."""
    return propose_knowledge(
        STORE,
        kind=kind,
        scope=scope,
        title=title,
        body=body,
        source_task_id=source_task_id,
        domain_id=domain_id,
        tags=tags,
    )


@mcp.tool()
def knowledge_decide(knowledge_id: str, decision: str, reason: str | None = None) -> dict[str, Any]:
    """Accept, reject, or deprecate a knowledge entry."""
    return decide_knowledge(STORE, knowledge_id=knowledge_id, decision=decision, reason=reason)


@mcp.tool()
def knowledge_update_list(
    status: str | None = None,
    domain_id: str | None = None,
) -> list[dict[str, Any]]:
    """List domain knowledge update proposals."""
    return list_knowledge_updates(STORE, status=status, domain_id=domain_id)


@mcp.tool()
def knowledge_update_read(update_id: str) -> dict[str, Any]:
    """Read one domain knowledge update proposal."""
    return read_knowledge_update(STORE, update_id=update_id)


@mcp.tool()
def knowledge_propose_update(
    domain_id: str,
    source_task_id: str,
    operation: str,
    proposal: dict[str, Any],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Propose a reviewed update to a domain SKILL.md."""
    return propose_knowledge_update(
        STORE,
        domain_id=domain_id,
        source_task_id=source_task_id,
        operation=operation,
        proposal=proposal,
        tags=tags,
    )


@mcp.tool()
def knowledge_decide_update(
    update_id: str,
    decision: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Accept or reject a domain knowledge update proposal."""
    return decide_knowledge_update(STORE, update_id=update_id, decision=decision, reason=reason)


@mcp.tool()
def execution_suggest_checks(repo_path: str | None = None) -> list[dict[str, Any]]:
    """Return named validation checks from the repo profile."""
    return suggest_checks(repo_path=repo_path)


@mcp.tool()
def execution_run_check(
    task_id: str,
    check_id: str,
    repo_path: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Run a named validation check and record stdout, stderr, exit code, and timing."""
    return run_check(
        STORE,
        task_id=task_id,
        check_id=check_id,
        repo_path=repo_path,
        timeout_seconds=timeout_seconds,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
