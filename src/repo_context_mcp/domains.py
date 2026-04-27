from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from .store import JsonStore, now_iso
from .workspace import read_profile

DOMAIN_DIR = "domains"


def list_domains(
    store: JsonStore,
    status: str | None = "active",
    repo_path: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    domains = []
    for domain_dir in _domains_root(store).glob("*"):
        if not domain_dir.is_dir():
            continue
        meta_path = domain_dir / "domain.json"
        if not meta_path.exists():
            continue
        metadata = _read_json(meta_path)
        if status and metadata.get("status") != status:
            continue
        if repo_path and str(Path(repo_path).expanduser().resolve()) not in metadata.get("repos", []):
            continue
        if tag and tag not in metadata.get("tags", []):
            continue
        domains.append(_public_metadata(metadata))
    return sorted(domains, key=lambda item: item.get("updated_at", ""), reverse=True)


def read_domain(store: JsonStore, domain_id: str) -> dict[str, Any]:
    domain_dir = _domain_path(store, domain_id)
    meta_path = domain_dir / "domain.json"
    skill_path = domain_dir / "SKILL.md"
    if not meta_path.exists() or not skill_path.exists():
        raise KeyError(f"domain not found: {domain_id}")
    metadata = _read_json(meta_path)
    return {
        "domain": _public_metadata(metadata),
        "skill_md": skill_path.read_text(encoding="utf-8"),
    }


def duplicate_domain_groups(
    store: JsonStore,
    status: str | None = "active",
    repo_path: str | None = None,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for domain in list_domains(store, status=status, repo_path=repo_path):
        groups.setdefault(_domain_match_key(domain), []).append(domain)

    duplicates = []
    for key, domains in groups.items():
        if len(domains) < 2:
            continue
        duplicates.append(
            {
                "key": key,
                "name": domains[0]["name"],
                "domains": domains,
                "recommended_target_id": _recommended_merge_target(domains),
            }
        )
    return sorted(duplicates, key=lambda item: item["name"].casefold())


def create_domain(
    store: JsonStore,
    name: str,
    description: str,
    repos: list[str] | None = None,
    tags: list[str] | None = None,
    body: str | None = None,
    domain_id: str | None = None,
) -> dict[str, Any]:
    now = now_iso()
    directory_name_source = "explicit"
    if domain_id is None:
        existing = _find_domain_by_name(store, name)
        if existing:
            return {"domain": existing, "created": False}
    repos = [_normalize_path(repo) for repo in repos or []]
    if domain_id is None:
        domain_id, directory_name_source = _unique_domain_id(
            store,
            name=name,
            description=description,
            repos=repos,
            tags=tags or [],
        )
    metadata = {
        "id": domain_id,
        "name": name,
        "description": description,
        "repos": sorted(set(repos)),
        "tags": sorted(set(tags or [])),
        "status": "active",
        "directory_name_source": directory_name_source,
        "created_at": now,
        "updated_at": now,
    }
    domain_dir = _domain_path(store, domain_id)
    if domain_dir.exists():
        existing = read_domain(store, domain_id)["domain"]
        return {"domain": existing, "created": False}

    domain_dir.mkdir(parents=True, exist_ok=True)
    _write_json(domain_dir / "domain.json", metadata)
    _write_text(domain_dir / "SKILL.md", _render_skill(metadata, body=body))
    return {"domain": _public_metadata(metadata), "created": True}


def merge_domains(
    store: JsonStore,
    target_domain_id: str,
    source_domain_ids: list[str],
    reason: str | None = None,
) -> dict[str, Any]:
    if not source_domain_ids:
        raise ValueError("source_domain_ids must include at least one domain")
    if target_domain_id in source_domain_ids:
        raise ValueError("target_domain_id cannot also be a source domain")

    target_dir = _domain_path(store, target_domain_id)
    target_meta_path = target_dir / "domain.json"
    target_skill_path = target_dir / "SKILL.md"
    if not target_meta_path.exists() or not target_skill_path.exists():
        raise KeyError(f"target domain not found: {target_domain_id}")

    source_ids = _dedupe_preserve_order(source_domain_ids)
    source_records = []
    for source_id in source_ids:
        source_dir = _domain_path(store, source_id)
        source_meta_path = source_dir / "domain.json"
        source_skill_path = source_dir / "SKILL.md"
        if not source_meta_path.exists() or not source_skill_path.exists():
            raise KeyError(f"source domain not found: {source_id}")
        source_records.append(
            {
                "id": source_id,
                "metadata": _read_json(source_meta_path),
                "skill_md": source_skill_path.read_text(encoding="utf-8").rstrip(),
                "meta_path": source_meta_path,
            }
        )

    now = now_iso()
    target_metadata = _read_json(target_meta_path)
    target_skill = target_skill_path.read_text(encoding="utf-8").rstrip()
    merged_sections = []
    for source in source_records:
        metadata = source["metadata"]
        target_metadata["repos"] = sorted(set(target_metadata.get("repos", [])) | set(metadata.get("repos", [])))
        target_metadata["tags"] = sorted(set(target_metadata.get("tags", [])) | set(metadata.get("tags", [])))
        source_reason = f"\n\nReason: {reason.strip()}" if reason else ""
        merged_sections.append(
            "\n\n"
            f"## Merged Domain: {metadata.get('name', source['id'])}\n\n"
            f"Source domain: `{source['id']}`.{source_reason}\n\n"
            f"{source['skill_md']}"
        )

    target_metadata["updated_at"] = now
    _write_json(target_meta_path, target_metadata)
    _write_text(target_skill_path, target_skill + "".join(merged_sections))

    remap_counts = _remap_domain_references(store, target_domain_id, source_ids)
    sources = []
    for source in source_records:
        source_metadata = source["metadata"]
        source_metadata["status"] = "merged"
        source_metadata["merged_into"] = target_domain_id
        source_metadata["merged_at"] = now
        source_metadata["merge_reason"] = reason
        source_metadata["updated_at"] = now
        _write_json(source["meta_path"], source_metadata)
        sources.append(_public_metadata(source_metadata))

    return {
        "target": _public_metadata(target_metadata),
        "sources": sources,
        "remapped": remap_counts,
    }


def rename_domain_directory(
    store: JsonStore,
    domain_id: str,
    new_domain_id: str | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    domain_dir = _domain_path(store, domain_id)
    meta_path = domain_dir / "domain.json"
    skill_path = domain_dir / "SKILL.md"
    if not meta_path.exists() or not skill_path.exists():
        raise KeyError(f"domain not found: {domain_id}")

    metadata = _read_json(meta_path)
    source = "explicit"
    if new_domain_id:
        slug = _slugify(new_domain_id)
    else:
        slug, source = _domain_directory_slug(
            name=metadata["name"],
            description=metadata.get("description", ""),
            repos=metadata.get("repos", []),
            tags=metadata.get("tags", []),
            allow_llm=use_llm,
        )

    candidate = _unique_domain_id_from_slug(store, slug, exclude_domain_id=domain_id)
    if candidate == domain_id:
        return {
            "domain": _public_metadata(metadata),
            "renamed": False,
            "old_domain_id": domain_id,
            "new_domain_id": domain_id,
            "remapped": {"tasks": 0, "knowledge": 0, "knowledge_updates": 0},
        }

    target_dir = _domain_path(store, candidate)
    if target_dir.exists():
        raise FileExistsError(f"domain directory already exists: {candidate}")

    previous_ids = metadata.get("previous_ids", [])
    metadata["id"] = candidate
    metadata["previous_ids"] = _dedupe_preserve_order([*previous_ids, domain_id])
    metadata["directory_name_source"] = source if not new_domain_id else "explicit"
    metadata["updated_at"] = now_iso()
    _write_json(meta_path, metadata)
    domain_dir.rename(target_dir)
    remapped = _remap_domain_references(store, candidate, [domain_id])
    return {
        "domain": _public_metadata(metadata),
        "renamed": True,
        "old_domain_id": domain_id,
        "new_domain_id": candidate,
        "remapped": remapped,
    }


def link_domain_repo(store: JsonStore, domain_id: str, repo_path: str) -> dict[str, Any]:
    domain_dir = _domain_path(store, domain_id)
    meta_path = domain_dir / "domain.json"
    if not meta_path.exists():
        raise KeyError(f"domain not found: {domain_id}")
    metadata = _read_json(meta_path)
    repo = _normalize_path(repo_path)
    repos = set(metadata.get("repos", []))
    repos.add(repo)
    metadata["repos"] = sorted(repos)
    metadata["updated_at"] = now_iso()
    _write_json(meta_path, metadata)
    return _public_metadata(metadata)


def domain_context(store: JsonStore, domain_ids: list[str] | None = None) -> list[dict[str, Any]]:
    if not domain_ids:
        return []
    contexts = []
    for domain_id in domain_ids:
        try:
            contexts.append(read_domain(store, domain_id))
        except KeyError:
            continue
    return contexts


def domain_catalog(store: JsonStore, repo_path: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "description": item["description"],
            "repos": item.get("repos", []),
            "tags": item.get("tags", []),
            "previous_ids": item.get("previous_ids", []),
        }
        for item in list_domains(store, repo_path=repo_path)
    ]


def resolve_domains(
    store: JsonStore,
    user_request: str,
    repo_path: str | None = None,
    domain_hint: str | None = None,
    use_llm: bool = True,
    create_if_missing: bool = False,
) -> dict[str, Any]:
    profile = read_profile(repo_path)
    catalog = domain_catalog(store)

    if domain_hint:
        hinted = _match_hint(catalog, domain_hint)
        if hinted:
            return {
                "llm_used": False,
                "matched_domains": [
                    {
                        "domain_id": hinted["id"],
                        "confidence": 1.0,
                        "reason": "Matched explicit domain_hint.",
                        "matched_by": ["domain_hint"],
                    }
                ],
                "new_domain_needed": False,
                "suggested_domain": None,
                "warnings": [],
            }

    fallback = _fallback_resolve(profile, catalog, user_request)
    warnings: list[str] = []

    if use_llm:
        try:
            from .llm import resolve_domain_with_openai

            llm_result = resolve_domain_with_openai(
                user_request=user_request,
                repo_profile=profile,
                domain_catalog=catalog,
                domain_hint=domain_hint,
            )
            if create_if_missing and llm_result.get("new_domain_needed") and llm_result.get("suggested_domain"):
                suggested = llm_result["suggested_domain"]
                created = create_domain(
                    store,
                    name=suggested["name"],
                    description=suggested["description"],
                    repos=[profile["repo_path"]],
                    tags=suggested.get("tags", []),
                )
                llm_result["created_domain"] = created["domain"]
            return llm_result
        except Exception as exc:
            warnings.append(f"LLM domain resolution unavailable: {exc}")

    fallback["warnings"] = warnings
    return fallback


def append_domain_skill_section(
    store: JsonStore,
    domain_id: str,
    heading: str,
    body: str,
    source_task_id: str | None = None,
) -> None:
    domain_dir = _domain_path(store, domain_id)
    skill_path = domain_dir / "SKILL.md"
    meta_path = domain_dir / "domain.json"
    if not skill_path.exists() or not meta_path.exists():
        raise KeyError(f"domain not found: {domain_id}")

    source = f"\n\nEvidence: task `{source_task_id}`." if source_task_id else ""
    current = skill_path.read_text(encoding="utf-8").rstrip()
    section = f"\n\n## {heading}\n\n{body.strip()}{source}\n"
    _write_text(skill_path, current + section)
    metadata = _read_json(meta_path)
    metadata["updated_at"] = now_iso()
    _write_json(meta_path, metadata)


def _fallback_resolve(
    profile: dict[str, Any],
    catalog: list[dict[str, Any]],
    user_request: str,
) -> dict[str, Any]:
    repo = profile["repo_path"]
    request = user_request.casefold()
    matches = []
    for domain in catalog:
        score = 0.0
        matched_by = []
        if repo in domain.get("repos", []):
            score += 0.75
            matched_by.append("repo")
        haystack = " ".join([domain.get("name", ""), domain.get("description", ""), " ".join(domain.get("tags", []))]).casefold()
        if any(term in haystack for term in request.split()):
            score += 0.2
            matched_by.append("text")
        if score:
            matches.append(
                {
                    "domain_id": domain["id"],
                    "confidence": min(score, 0.95),
                    "reason": "Deterministic fallback matched repo or request text.",
                    "matched_by": matched_by,
                }
            )
    matches.sort(key=lambda item: item["confidence"], reverse=True)
    return {
        "llm_used": False,
        "matched_domains": matches[:3],
        "new_domain_needed": not bool(matches),
        "suggested_domain": _suggest_domain(profile) if not matches else None,
    }


def _suggest_domain(profile: dict[str, Any]) -> dict[str, Any]:
    name = profile.get("name", "Repository Knowledge")
    languages = profile.get("languages", [])
    tags = [*languages]
    return {
        "name": f"{name} Domain",
        "description": profile.get("summary") or f"Knowledge for working in {name}.",
        "tags": tags,
    }


def _match_hint(catalog: list[dict[str, Any]], hint: str) -> dict[str, Any] | None:
    normalized = hint.casefold()
    for domain in catalog:
        aliases = {
            domain["id"].casefold(),
            domain["name"].casefold(),
            *[item.casefold() for item in domain.get("previous_ids", [])],
        }
        if normalized in aliases:
            return domain
    return None


def _find_domain_by_name(store: JsonStore, name: str) -> dict[str, Any] | None:
    normalized = name.casefold()
    for domain in list_domains(store, status=None):
        if domain["status"] == "active" and domain["name"].casefold() == normalized:
            return domain
    return None


def _domain_match_key(domain: dict[str, Any]) -> str:
    return _slugify(domain["name"])


def _recommended_merge_target(domains: list[dict[str, Any]]) -> str:
    canonical_id = _slugify(domains[0]["name"])
    legacy_id = f"d_{canonical_id}"
    for preferred_id in (canonical_id, legacy_id):
        for domain in domains:
            if domain["id"] == preferred_id:
                return domain["id"]
    return sorted(domains, key=lambda item: item.get("created_at") or "")[0]["id"]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _remap_domain_references(store: JsonStore, target_domain_id: str, source_domain_ids: list[str]) -> dict[str, int]:
    source_set = set(source_domain_ids)
    counts = {
        "tasks": 0,
        "knowledge": 0,
        "knowledge_updates": 0,
    }

    tasks = store.read_collection("tasks")
    for task in tasks:
        original = task.get("domain_ids", [])
        if not isinstance(original, list) or not source_set.intersection(original):
            continue
        task["domain_ids"] = _dedupe_preserve_order(
            [target_domain_id if domain_id in source_set else domain_id for domain_id in original]
        )
        counts["tasks"] += 1
    store.write_collection("tasks", tasks)

    for collection in ("knowledge", "knowledge_updates"):
        items = store.read_collection(collection)
        for item in items:
            if item.get("domain_id") in source_set:
                item["domain_id"] = target_domain_id
                counts[collection] += 1
        store.write_collection(collection, items)

    return counts


def _render_skill(metadata: dict[str, Any], body: str | None = None) -> str:
    frontmatter = {
        "name": metadata["name"],
        "description": metadata["description"],
        "tags": metadata["tags"],
        "repos": metadata["repos"],
        "status": metadata["status"],
    }
    default_body = f"""# {metadata["name"]}

## When To Use

Use this domain when {metadata["description"].rstrip(".").lower()}.

## Conventions

- Keep durable knowledge concise, scoped, and backed by task evidence.

## Workflows

- Resolve this domain before starting related repo work.
- Propose updates during a task and accept them only after review.

## Known Pitfalls

- Do not treat one-off task notes as durable domain knowledge without review.

## Evidence

- Created at {metadata["created_at"]}.
"""
    return f"---\n{json.dumps(frontmatter, ensure_ascii=False, indent=2)}\n---\n\n{body or default_body}"


def _unique_domain_id(
    store: JsonStore,
    name: str,
    description: str,
    repos: list[str],
    tags: list[str],
) -> tuple[str, str]:
    slug, source = _domain_directory_slug(
        name=name,
        description=description,
        repos=repos,
        tags=tags,
    )
    return _unique_domain_id_from_slug(store, slug), source


def _unique_domain_id_from_slug(
    store: JsonStore,
    slug: str,
    exclude_domain_id: str | None = None,
) -> str:
    candidate = slug
    index = 2
    while _domain_path(store, candidate).exists() and candidate != exclude_domain_id:
        candidate = f"{slug}-{index}"
        index += 1
    return candidate


def _domain_directory_slug(
    name: str,
    description: str,
    repos: list[str],
    tags: list[str],
    allow_llm: bool = True,
) -> tuple[str, str]:
    mode = (
        os.environ.get("REPO_CONTEXT_DOMAIN_NAMING")
        or os.environ.get("AGENT_SUBSTRATE_DOMAIN_NAMING")
        or "auto"
    )
    if mode not in {"auto", "llm", "deterministic"}:
        mode = "auto"
    if not allow_llm:
        mode = "deterministic"
    if mode != "deterministic":
        try:
            from .llm import generate_domain_directory_name_with_openai

            generated = generate_domain_directory_name_with_openai(
                name=name,
                description=description,
                repos=repos,
                tags=tags,
            )
            slug = _slugify(generated)
            if slug:
                return slug, "llm"
        except Exception:
            if mode == "llm":
                raise
    return _slugify(name), "deterministic"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or uuid4().hex[:8]


def _domains_root(store: JsonStore) -> Path:
    return store.root / DOMAIN_DIR


def _domain_path(store: JsonStore, domain_id: str) -> Path:
    if "/" in domain_id or ".." in domain_id:
        raise ValueError("domain_id must not contain path separators")
    return _domains_root(store) / domain_id


def _normalize_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    public = {
        "id": metadata["id"],
        "name": metadata["name"],
        "description": metadata.get("description", ""),
        "repos": metadata.get("repos", []),
        "tags": metadata.get("tags", []),
        "status": metadata.get("status", "active"),
        "previous_ids": metadata.get("previous_ids", []),
        "directory_name_source": metadata.get("directory_name_source"),
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
    }
    if metadata.get("merged_into"):
        public["merged_into"] = metadata["merged_into"]
        public["merged_at"] = metadata.get("merged_at")
    return public


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()
