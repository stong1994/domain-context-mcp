from __future__ import annotations

from typing import Any
from uuid import uuid4

from .domains import domain_context, resolve_domains
from .knowledge import list_knowledge, list_knowledge_updates
from .store import JsonStore, now_iso
from .workspace import resolve_repo, workspace_context

COLLECTION = "tasks"


def begin_task(
    store: JsonStore,
    user_request: str,
    repo_path: str | None = None,
    domain_hint: str | None = None,
    conversation_id: str | None = None,
    idempotency_key: str | None = None,
    resolve_domain_context: bool = True,
) -> dict[str, Any]:
    context = workspace_context(repo_path)
    existing = find_current_task(
        store,
        repo_path=context["repo"]["path"],
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
    )
    domain_resolution = (
        resolve_domains(
            store,
            user_request=user_request,
            repo_path=context["repo"]["path"],
            domain_hint=domain_hint,
            use_llm=True,
        )
        if resolve_domain_context
        else {
            "llm_used": False,
            "matched_domains": [],
            "new_domain_needed": False,
            "suggested_domain": None,
            "warnings": [],
        }
    )
    domain_ids = [item["domain_id"] for item in domain_resolution.get("matched_domains", [])]

    if existing:
        return {
            "task": existing,
            "created": False,
            "workspace_context": context,
            "domain_resolution": domain_resolution,
            "domain_context": domain_context(store, existing.get("domain_ids", domain_ids)),
            "recommended_next_tools": _recommended_next_tools(),
        }

    task = {
        "id": f"t_{uuid4().hex[:12]}",
        "status": "active",
        "user_request": user_request,
        "repo_path": context["repo"]["path"],
        "domain_ids": domain_ids,
        "conversation_id": conversation_id,
        "idempotency_key": idempotency_key,
        "created_at": now_iso(),
        "completed_at": None,
    }
    store.append(COLLECTION, task)
    return {
        "task": task,
        "created": True,
        "workspace_context": context,
        "domain_resolution": domain_resolution,
        "domain_context": domain_context(store, domain_ids),
        "recommended_next_tools": _recommended_next_tools(),
    }


def list_tasks(
    store: JsonStore,
    status: str | None = None,
    repo_path: str | None = None,
    conversation_id: str | None = None,
) -> list[dict[str, Any]]:
    items = store.read_collection(COLLECTION)
    if status:
        items = [item for item in items if item.get("status") == status]
    if repo_path:
        items = [item for item in items if item.get("repo_path") == repo_path]
    if conversation_id:
        items = [item for item in items if item.get("conversation_id") == conversation_id]
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def find_current_task(
    store: JsonStore,
    repo_path: str | None = None,
    conversation_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    resolved_repo = str(resolve_repo(repo_path)) if repo_path else None
    active = list_tasks(store, status="active", repo_path=resolved_repo)
    if idempotency_key:
        for item in active:
            if item.get("idempotency_key") == idempotency_key:
                return item
    if conversation_id:
        for item in active:
            if item.get("conversation_id") == conversation_id:
                return item
    return None


def resume_task(store: JsonStore, task_id: str) -> dict[str, Any]:
    task = store.get_by_id(COLLECTION, task_id)
    if task.get("status") != "active":
        task = store.update_by_id(COLLECTION, task_id, {"status": "active", "completed_at": None})
    return task


def complete_task(store: JsonStore, task_id: str) -> dict[str, Any]:
    task = store.get_by_id(COLLECTION, task_id)
    runs = [
        item
        for item in store.read_collection("executions")
        if item.get("task_id") == task_id
    ]
    proposed = [
        item
        for item in list_knowledge(store, status="proposed")
        if item.get("source_task_id") == task_id
    ]
    proposed_updates = [
        item
        for item in list_knowledge_updates(store, status="proposed")
        if item.get("source_task_id") == task_id
    ]

    warnings: list[str] = []
    if not runs:
        warnings.append("No execution checks recorded for this task.")
    failed = [run for run in runs if run.get("exit_code") != 0]
    if failed:
        warnings.append(f"{len(failed)} execution check(s) failed.")
    if proposed:
        warnings.append(f"{len(proposed)} knowledge proposal(s) still need review.")
    if proposed_updates:
        warnings.append(f"{len(proposed_updates)} domain knowledge update(s) still need review.")

    status = "completed_with_warnings" if warnings else "completed"
    updated = store.update_by_id(
        COLLECTION,
        task_id,
        {
            "status": status,
            "completed_at": now_iso(),
        },
    )
    return {
        "task": updated,
        "warnings": warnings,
        "execution_count": len(runs),
        "pending_knowledge_count": len(proposed) + len(proposed_updates),
    }


def _recommended_next_tools() -> list[str]:
    return [
        "domain_resolve",
        "knowledge_search",
        "execution_suggest_checks",
        "execution_run_check",
        "knowledge_propose_update",
        "knowledge_decide_update",
        "task_complete",
    ]
