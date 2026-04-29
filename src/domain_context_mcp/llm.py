from __future__ import annotations

import json
import os
from typing import Any

from .auth import resolve_openai_api_key


def _env(name: str, legacy_name: str | None = None, default: str | None = None) -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    if legacy_name:
        legacy_value = os.environ.get(legacy_name)
        if legacy_value is not None:
            return legacy_value
    if default is None:
        raise KeyError(name)
    return default


DOMAIN_RESOLVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "llm_used",
        "matched_domains",
        "new_domain_needed",
        "suggested_domain",
        "warnings",
    ],
    "properties": {
        "llm_used": {"type": "boolean"},
        "matched_domains": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["domain_id", "confidence", "reason", "matched_by"],
                "properties": {
                    "domain_id": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                    "matched_by": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "new_domain_needed": {"type": "boolean"},
        "suggested_domain": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "description", "tags"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ]
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}

DOMAIN_DIRECTORY_NAME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["directory_name"],
    "properties": {
        "directory_name": {
            "type": "string",
            "description": "A concise, human-readable kebab-case directory name.",
        },
    },
}


def resolve_domain_with_openai(
    user_request: str,
    repo_profile: dict[str, Any],
    domain_catalog: list[dict[str, Any]],
    domain_hint: str | None = None,
) -> dict[str, Any]:
    api_key = resolve_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is not configured. Set DOMAIN_CONTEXT_OPENAI_API_KEY, "
            "OPENAI_API_KEY, or run domain-context-auth login --with-api-key."
        )

    from openai import OpenAI

    model = _env(
        "DOMAIN_CONTEXT_MODEL",
        "REPO_CONTEXT_MODEL",
        os.environ.get("AGENT_SUBSTRATE_MODEL", "gpt-5.2-codex"),
    )
    client = OpenAI(api_key=api_key)
    payload = {
        "user_request": user_request,
        "repo_profile": repo_profile,
        "domain_hint": domain_hint,
        "domain_catalog": domain_catalog,
    }
    prompt = (
        "Resolve which skill-like knowledge domains apply to this coding-agent task. "
        "Prefer existing domains when they are semantically appropriate. "
        "Set new_domain_needed only when no existing domain should own the durable knowledge. "
        "Return only JSON matching the schema."
    )
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "domain_resolution",
                "schema": DOMAIN_RESOLVE_SCHEMA,
                "strict": True,
            }
        },
        reasoning={
            "effort": _env(
                "DOMAIN_CONTEXT_REASONING",
                "REPO_CONTEXT_REASONING",
                os.environ.get("AGENT_SUBSTRATE_REASONING", "medium"),
            )
        },
    )
    parsed = json.loads(response.output_text)
    parsed["llm_used"] = True
    return parsed


def generate_domain_directory_name_with_openai(
    name: str,
    description: str,
    repos: list[str] | None = None,
    tags: list[str] | None = None,
) -> str:
    api_key = resolve_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is not configured. Set DOMAIN_CONTEXT_OPENAI_API_KEY, "
            "OPENAI_API_KEY, or run domain-context-auth login --with-api-key."
        )

    from openai import OpenAI

    model = _env(
        "DOMAIN_CONTEXT_MODEL",
        "REPO_CONTEXT_MODEL",
        os.environ.get("AGENT_SUBSTRATE_MODEL", "gpt-5.2-codex"),
    )
    client = OpenAI(api_key=api_key)
    payload = {
        "name": name,
        "description": description,
        "repos": repos or [],
        "tags": tags or [],
    }
    prompt = (
        "Generate a directory name for a coding-agent knowledge domain. "
        "The name must be easy for humans to recognize in a filesystem, concise, "
        "kebab-case, ASCII lowercase, and 2-6 words. Do not use opaque prefixes "
        "like d_, ids, hashes, dates, or random suffixes. Return only JSON matching the schema."
    )
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "domain_directory_name",
                "schema": DOMAIN_DIRECTORY_NAME_SCHEMA,
                "strict": True,
            }
        },
        reasoning={
            "effort": _env(
                "DOMAIN_CONTEXT_REASONING",
                "REPO_CONTEXT_REASONING",
                os.environ.get("AGENT_SUBSTRATE_REASONING", "medium"),
            )
        },
    )
    parsed = json.loads(response.output_text)
    return parsed["directory_name"]
