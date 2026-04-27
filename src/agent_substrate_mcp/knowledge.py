from __future__ import annotations

from typing import Any
from uuid import uuid4

from .domains import append_domain_skill_section, read_domain
from .store import JsonStore, now_iso

COLLECTION = "knowledge"
UPDATES_COLLECTION = "knowledge_updates"
ACTIVE_STATUSES = {"accepted", "active"}


def list_knowledge(
    store: JsonStore,
    status: str | None = None,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    items = store.read_collection(COLLECTION)
    if status:
        items = [item for item in items if item.get("status") == status]
    if scope:
        items = [item for item in items if item.get("scope") == scope]
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def read_knowledge(store: JsonStore, knowledge_id: str) -> dict[str, Any]:
    return store.get_by_id(COLLECTION, knowledge_id)


def search_knowledge(
    store: JsonStore,
    query: str,
    scope: str | None = None,
    domain_id: str | None = None,
    status: str = "active",
    limit: int = 10,
) -> list[dict[str, Any]]:
    query_terms = [term.casefold() for term in query.split() if term.strip()]
    items = list_knowledge(store, scope=scope)
    if domain_id:
        items = [item for item in items if item.get("domain_id") == domain_id]
    if status == "active":
        items = [item for item in items if item.get("status") in ACTIVE_STATUSES]
    elif status:
        items = [item for item in items if item.get("status") == status]

    scored: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        haystack = " ".join(
            [
                item.get("title", ""),
                item.get("body", ""),
                item.get("kind", ""),
                " ".join(item.get("tags", [])),
            ]
        ).casefold()
        score = sum(1 for term in query_terms if term in haystack)
        if not query_terms or score:
            scored.append((score, item))

    if domain_id:
        try:
            domain = read_domain(store, domain_id)
            skill_md = domain["skill_md"]
            haystack = skill_md.casefold()
            score = sum(1 for term in query_terms if term in haystack)
            if not query_terms or score:
                scored.append(
                    (
                        score,
                        {
                            "id": f"{domain_id}:SKILL.md",
                            "kind": "domain_skill",
                            "domain_id": domain_id,
                            "scope": f"domain:{domain_id}",
                            "title": domain["domain"]["name"],
                            "body": _excerpt(skill_md, query_terms),
                            "status": "active",
                            "tags": domain["domain"].get("tags", []),
                            "created_at": domain["domain"].get("created_at", ""),
                        },
                    )
                )
        except KeyError:
            pass

    scored.sort(key=lambda pair: (pair[0], pair[1].get("created_at", "")), reverse=True)
    return [item for _, item in scored[:limit]]


def propose_knowledge(
    store: JsonStore,
    kind: str,
    scope: str,
    title: str,
    body: str,
    source_task_id: str | None = None,
    domain_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    item = {
        "id": f"k_{uuid4().hex[:12]}",
        "domain_id": domain_id,
        "kind": kind,
        "scope": scope,
        "title": title,
        "body": body,
        "status": "proposed",
        "source_task_id": source_task_id,
        "source_task_ids": [source_task_id] if source_task_id else [],
        "tags": tags or [],
        "created_at": now_iso(),
        "decided_at": None,
        "decision_reason": None,
    }
    return store.append(COLLECTION, item)


def decide_knowledge(
    store: JsonStore,
    knowledge_id: str,
    decision: str,
    reason: str | None = None,
) -> dict[str, Any]:
    if decision not in {"accept", "reject", "deprecate"}:
        raise ValueError("decision must be accept, reject, or deprecate")

    item = store.get_by_id(COLLECTION, knowledge_id)
    if decision in {"accept", "reject"} and item.get("status") != "proposed":
        raise ValueError("only proposed knowledge can be accepted or rejected")
    if decision == "deprecate" and item.get("status") not in ACTIVE_STATUSES:
        raise ValueError("only active knowledge can be deprecated")

    status = {"accept": "accepted", "reject": "rejected", "deprecate": "deprecated"}[decision]
    return store.update_by_id(
        COLLECTION,
        knowledge_id,
        {
            "status": status,
            "decided_at": now_iso(),
            "decision_reason": reason,
        },
    )


def list_knowledge_updates(
    store: JsonStore,
    status: str | None = None,
    domain_id: str | None = None,
) -> list[dict[str, Any]]:
    items = store.read_collection(UPDATES_COLLECTION)
    if status:
        items = [item for item in items if item.get("status") == status]
    if domain_id:
        items = [item for item in items if item.get("domain_id") == domain_id]
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def read_knowledge_update(store: JsonStore, update_id: str) -> dict[str, Any]:
    return store.get_by_id(UPDATES_COLLECTION, update_id)


def propose_knowledge_update(
    store: JsonStore,
    domain_id: str,
    source_task_id: str,
    operation: str,
    proposal: dict[str, Any],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    if operation not in {"create", "update", "deprecate"}:
        raise ValueError("operation must be create, update, or deprecate")
    if "title" not in proposal or "body" not in proposal:
        raise ValueError("proposal must include title and body")
    read_domain(store, domain_id)
    item = {
        "id": f"ku_{uuid4().hex[:12]}",
        "domain_id": domain_id,
        "source_task_id": source_task_id,
        "operation": operation,
        "proposal": proposal,
        "tags": tags or [],
        "status": "proposed",
        "decision": None,
        "decision_reason": None,
        "resulting_knowledge_id": None,
        "created_at": now_iso(),
        "decided_at": None,
    }
    return store.append(UPDATES_COLLECTION, item)


def decide_knowledge_update(
    store: JsonStore,
    update_id: str,
    decision: str,
    reason: str | None = None,
) -> dict[str, Any]:
    if decision not in {"accept", "reject"}:
        raise ValueError("decision must be accept or reject")
    item = store.get_by_id(UPDATES_COLLECTION, update_id)
    if item.get("status") != "proposed":
        raise ValueError("only proposed knowledge updates can be decided")

    resulting_knowledge_id = None
    if decision == "accept":
        proposal = item["proposal"]
        knowledge = propose_knowledge(
            store,
            kind=proposal.get("kind", item["operation"]),
            scope=proposal.get("scope", f"domain:{item['domain_id']}"),
            title=proposal["title"],
            body=proposal["body"],
            source_task_id=item["source_task_id"],
            domain_id=item["domain_id"],
            tags=item.get("tags", []),
        )
        knowledge = decide_knowledge(store, knowledge["id"], "accept", reason=reason)
        resulting_knowledge_id = knowledge["id"]
        append_domain_skill_section(
            store,
            item["domain_id"],
            heading=proposal["title"],
            body=proposal["body"],
            source_task_id=item["source_task_id"],
        )

    return store.update_by_id(
        UPDATES_COLLECTION,
        update_id,
        {
            "status": "accepted" if decision == "accept" else "rejected",
            "decision": decision,
            "decision_reason": reason,
            "resulting_knowledge_id": resulting_knowledge_id,
            "decided_at": now_iso(),
        },
    )


def _excerpt(text: str, query_terms: list[str], limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    folded = text.casefold()
    indexes = [folded.find(term) for term in query_terms if term in folded]
    start = max(min(indexes) - 200, 0) if indexes else 0
    return text[start : start + limit]
