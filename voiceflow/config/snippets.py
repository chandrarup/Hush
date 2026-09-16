"""Persistent spoken shortcuts for frequently used text."""

from __future__ import annotations

import os
import hashlib
import json
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

import toml

from .paths import CONFIG_DIR, SNIPPETS_PATH


_STORE_LOCK = threading.RLock()


class SnippetStoreError(ValueError):
    """Raised when the persisted snippet store cannot be read safely."""


def _normalise_text(value: str) -> str:
    """Normalize a shortcut for matching while preserving saved text exactly."""
    normalized = " ".join(value.casefold().strip().split())
    return re.sub(r"[.!?]+$", "", normalized).strip()


def _normalise(data: dict[str, Any] | None, *, strict: bool = False) -> list[dict[str, str]]:
    if not isinstance(data, dict) or "snippets" not in data:
        if strict:
            raise SnippetStoreError("Snippet file must contain a 'snippets' list.")
        return []

    entries = data["snippets"]
    if not isinstance(entries, list):
        if strict:
            raise SnippetStoreError("Snippet file 'snippets' value must be a list.")
        return []

    snippets = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            if strict:
                raise SnippetStoreError(f"Snippet {index} must be an object.")
            continue
        name = item.get("name", "")
        shortcut = item.get("shortcut", "")
        text = item.get("text", "")
        if strict and not all(isinstance(value, str) for value in (name, shortcut, text)):
            raise SnippetStoreError(f"Snippet {index} fields must be strings.")
        name = str(name).strip()
        shortcut = str(shortcut).strip()
        text = str(text).strip()
        if name and shortcut and text and _normalise_text(shortcut):
            snippets.append({"name": name, "shortcut": shortcut, "text": text})
        elif strict:
            raise SnippetStoreError(f"Snippet {index} has missing or invalid fields.")
    return snippets


def load_snippets() -> list[dict[str, str]]:
    """Load saved snippets, propagating malformed or unreadable files."""
    if not SNIPPETS_PATH.exists():
        return []
    with _STORE_LOCK:
        try:
            data = toml.load(str(SNIPPETS_PATH))
            return _normalise(data, strict=True)
        except SnippetStoreError:
            raise
        except Exception as exc:
            raise SnippetStoreError(f"Could not read {SNIPPETS_PATH}: {exc}") from exc


def get_snippets_snapshot() -> tuple[list[dict[str, str]], str]:
    """Return the current snippets and a stable version for conditional writes."""
    with _STORE_LOCK:
        snippets = load_snippets()
        return snippets, _version(snippets)


def _version(snippets: list[dict[str, str]]) -> str:
    payload = json.dumps(snippets, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _save(snippets: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = _normalise({"snippets": snippets})
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    descriptor, temporary_name = tempfile.mkstemp(
        dir=CONFIG_DIR,
        prefix=f".{SNIPPETS_PATH.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            toml.dump({"snippets": normalized}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, SNIPPETS_PATH)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
    return normalized


def add_snippet(name: str, shortcut: str, text: str) -> list[dict[str, str]]:
    """Create or update a snippet using its spoken shortcut as the key."""
    name, shortcut, text = _validated_fields(name, shortcut, text)

    with _STORE_LOCK:
        snippets = load_snippets()
        normalized_shortcut = _normalise_text(shortcut)
        for snippet in snippets:
            if _normalise_text(snippet["shortcut"]) == normalized_shortcut:
                snippet.update({"name": name, "shortcut": shortcut, "text": text})
                return _save(snippets)

        snippets.append({"name": name, "shortcut": shortcut, "text": text})
        return _save(snippets)


def update_snippet(index: int, name: str, shortcut: str, text: str) -> list[dict[str, str]]:
    """Update one snippet while preventing duplicate spoken shortcuts."""
    name, shortcut, text = _validated_fields(name, shortcut, text)
    with _STORE_LOCK:
        snippets = load_snippets()
        if index < 0 or index >= len(snippets):
            raise IndexError("Snippet does not exist.")

        normalized_shortcut = _normalise_text(shortcut)
        for position, snippet in enumerate(snippets):
            if position != index and _normalise_text(snippet["shortcut"]) == normalized_shortcut:
                raise ValueError("A snippet with this spoken shortcut already exists.")

        snippets[index] = {"name": name, "shortcut": shortcut, "text": text}
        return _save(snippets)


def _validated_fields(name: str, shortcut: str, text: str) -> tuple[str, str, str]:
    name = name.strip()
    shortcut = shortcut.strip()
    text = text.strip()
    if not name or not shortcut or not text or not _normalise_text(shortcut):
        raise ValueError("Name, spoken shortcut, and expanded text are required.")
    return name, shortcut, text


class SnippetConflictError(ValueError):
    """Raised when a mutation uses a stale snippet-list version."""


def remove_snippet(index: int, expected_version: str) -> list[dict[str, str]]:
    with _STORE_LOCK:
        snippets = load_snippets()
        if _version(snippets) != expected_version:
            raise SnippetConflictError("The snippet list changed. Reload and try again.")
        if index < 0 or index >= len(snippets):
            raise IndexError("Snippet does not exist.")
        snippets.pop(index)
        return _save(snippets)


def is_exact_shortcut(text: str, snippets: list[dict[str, str]]) -> bool:
    """Return whether a transcript is exactly one configured shortcut."""
    normalized_text = _normalise_text(text)
    if not normalized_text:
        return False
    return any(_normalise_text(item["shortcut"]) == normalized_text for item in snippets)


def expand_snippets(text: str, snippets: list[dict[str, str]]) -> str:
    """Expand configured shortcuts in a transcript."""
    if not _normalise_text(text):
        return text
    expanded = text
    for snippet in sorted(snippets, key=lambda item: len(_normalise_text(item["shortcut"])), reverse=True):
        if _normalise_text(snippet["shortcut"]) != _normalise_text(text):
            continue
        expanded = snippet["text"]
        break
    return expanded
