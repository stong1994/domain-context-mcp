from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def tail(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


@dataclass(frozen=True)
class JsonStore:
    root: Path

    @classmethod
    def from_env(cls) -> "JsonStore":
        root = (
            os.environ.get("DOMAIN_CONTEXT_HOME")
            or os.environ.get("REPO_CONTEXT_HOME")
            or os.environ.get("AGENT_SUBSTRATE_HOME")
            or "~/.domain-context-mcp"
        )
        return cls(Path(root).expanduser())

    def path(self, collection: str) -> Path:
        return self.root / f"{collection}.json"

    def read_collection(self, collection: str) -> list[dict[str, Any]]:
        path = self.path(collection)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"Collection {collection} must contain a JSON list")
        return data

    def write_collection(self, collection: str, items: list[dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path(collection)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{collection}.", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(items, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, path)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink()

    def append(self, collection: str, item: dict[str, Any]) -> dict[str, Any]:
        items = self.read_collection(collection)
        items.append(item)
        self.write_collection(collection, items)
        return item

    def update_by_id(
        self,
        collection: str,
        item_id: str,
        updates: dict[str, Any],
        id_field: str = "id",
    ) -> dict[str, Any]:
        items = self.read_collection(collection)
        for item in items:
            if item.get(id_field) == item_id:
                item.update(updates)
                self.write_collection(collection, items)
                return item
        raise KeyError(f"{collection} item not found: {item_id}")

    def get_by_id(self, collection: str, item_id: str, id_field: str = "id") -> dict[str, Any]:
        for item in self.read_collection(collection):
            if item.get(id_field) == item_id:
                return item
        raise KeyError(f"{collection} item not found: {item_id}")
