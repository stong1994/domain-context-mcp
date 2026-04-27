from __future__ import annotations

from typing import Any
from uuid import uuid4

from .execution import run_check, suggest_checks
from .knowledge import (
    decide_knowledge_update,
    list_knowledge_updates,
    propose_knowledge_update,
    search_knowledge,
)
from .store import JsonStore, now_iso
from .tasks import begin_task, complete_task
from .workspace import workspace_context

CHECKPOINTS_COLLECTION = "checkpoints"


def work_begin(
    store: JsonStore,
    user_request: str,
    repo_path: str | None = None,
    conversation_id: str | None = None,
    idempotency_key: str | None = None,
    domain_hint: str | None = None,
    knowledge_query: str | None = None,
    knowledge_limit: int = 5,
) -> dict[str, Any]:
    started = begin_task(
        store,
        user_request=user_request,
        repo_path=repo_path,
        domain_hint=domain_hint,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
        resolve_domain_context=True,
    )
    task = started["task"]
    context = started["workspace_context"]
    query = knowledge_query or user_request
    relevant_knowledge = _search_related_knowledge(
        store,
        query=query,
        domain_ids=task.get("domain_ids", []),
        limit=knowledge_limit,
    )
    checks = suggest_checks(context["repo"]["path"])
    return {
        **started,
        "relevant_knowledge": relevant_knowledge,
        "suggested_checks": checks,
    }


def work_checkpoint(
    store: JsonStore,
    task_id: str,
    summary: str,
    repo_path: str | None = None,
    run_check_ids: list[str] | None = None,
    knowledge_updates: list[dict[str, Any]] | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    checkpoint = {
        "id": f"cp_{uuid4().hex[:12]}",
        "task_id": task_id,
        "summary": summary,
        "created_at": now_iso(),
    }
    store.append(CHECKPOINTS_COLLECTION, checkpoint)

    executions = [
        run_check(store, task_id=task_id, check_id=check_id, repo_path=repo_path, timeout_seconds=timeout_seconds)
        for check_id in run_check_ids or []
    ]
    proposed_updates = [
        _propose_update_from_payload(store, task_id, payload)
        for payload in knowledge_updates or []
    ]
    return {
        "checkpoint": checkpoint,
        "executions": executions,
        "proposed_updates": proposed_updates,
    }


def work_finish(
    store: JsonStore,
    task_id: str,
    summary: str,
    repo_path: str | None = None,
    run_check_ids: list[str] | None = None,
    require_clean: bool = False,
    allow_pending_updates: bool = False,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    checkpoint_result = work_checkpoint(
        store,
        task_id=task_id,
        summary=summary,
        repo_path=repo_path,
        run_check_ids=run_check_ids,
        timeout_seconds=timeout_seconds,
    )
    context = workspace_context(repo_path)
    pending_updates = [
        item
        for item in list_knowledge_updates(store, status="proposed")
        if item.get("source_task_id") == task_id
    ]
    completion = complete_task(store, task_id)
    warnings = list(completion["warnings"])
    if require_clean and context["git"]["dirty"]:
        warnings.append("Repository has uncommitted changes.")

    failed_executions = [
        execution
        for execution in checkpoint_result["executions"]
        if execution.get("exit_code") != 0
    ]
    blocking_warnings = [
        warning
        for warning in warnings
        if not (allow_pending_updates and "knowledge update" in warning.casefold())
    ]
    ready = not failed_executions and not blocking_warnings

    return {
        "task": completion["task"],
        "checkpoint": checkpoint_result["checkpoint"],
        "executions": checkpoint_result["executions"],
        "pending_updates": pending_updates,
        "warnings": warnings,
        "ready": ready,
    }


def learning_review(
    store: JsonStore,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted = []
    rejected = []
    errors = []
    for decision in decisions:
        try:
            result = decide_knowledge_update(
                store,
                update_id=decision["update_id"],
                decision=decision["decision"],
                reason=decision.get("reason"),
            )
            if result["status"] == "accepted":
                accepted.append(result)
            else:
                rejected.append(result)
        except Exception as exc:
            errors.append(
                {
                    "update_id": decision.get("update_id"),
                    "error": str(exc),
                }
            )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "errors": errors,
    }


def _search_related_knowledge(
    store: JsonStore,
    query: str,
    domain_ids: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if not domain_ids:
        return search_knowledge(store, query=query, limit=limit)
    results: list[dict[str, Any]] = []
    for domain_id in domain_ids:
        results.extend(search_knowledge(store, query=query, domain_id=domain_id, limit=limit))
    return results[:limit]


def _propose_update_from_payload(
    store: JsonStore,
    task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return propose_knowledge_update(
        store,
        domain_id=payload["domain_id"],
        source_task_id=payload.get("source_task_id", task_id),
        operation=payload.get("operation", "create"),
        proposal=payload["proposal"],
        tags=payload.get("tags"),
    )
