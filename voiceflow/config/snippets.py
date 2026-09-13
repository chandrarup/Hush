"""Persistent spoken shortcuts for frequently used text."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import toml

from .loader import CONFIG_DIR


SNIPPETS_PATH = CONFIG_DIR / "snippets.toml"


def _normalise_text(value: str) -> str:
    """Normalize a shortcut for matching while preserving saved text exactly."""
    normalized = " ".join(value.casefold().strip().split())
    return re.sub(r"[.!?]+$", "", normalized).strip()


def _normalise(data: dict[str, Any] | None) -> list[dict[str, str]]:
    entries = (data or {}).get("snippets", [])
    if not isinstance(entries, list):
        return []

    snippets = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        shortcut = str(item.get("shortcut", "")).strip()
        text = str(item.get("text", "")).strip()
        if name and shortcut and text:
            snippets.append({"name": name, "shortcut": shortcut, "text": text})
    return snippets


def load_snippets() -> list[dict[str, str]]:
    """Load saved snippets, returning an empty list when none exist."""
    if not SNIPPETS_PATH.exists():
        return []
    try:
        return _normalise(toml.load(str(SNIPPETS_PATH)))
    except Exception as exc:
        print(f"[snippets] WARNING: Could not read {SNIPPETS_PATH}: {exc}")
        return []


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
    name = name.strip()
    shortcut = shortcut.strip()
    text = text.strip()
    if not name or not shortcut or not text:
        raise ValueError("Name, spoken shortcut, and expanded text are required.")

    snippets = load_snippets()
    normalized_shortcut = _normalise_text(shortcut)
    for snippet in snippets:
        if _normalise_text(snippet["shortcut"]) == normalized_shortcut:
            snippet.update({"name": name, "shortcut": shortcut, "text": text})
            return _save(snippets)

    snippets.append({"name": name, "shortcut": shortcut, "text": text})
    return _save(snippets)


def remove_snippet(index: int) -> list[dict[str, str]]:
    snippets = load_snippets()
    if index < 0 or index >= len(snippets):
        raise IndexError("Snippet does not exist.")
    snippets.pop(index)
    return _save(snippets)


def is_exact_shortcut(text: str, snippets: list[dict[str, str]]) -> bool:
    """Return whether a transcript is exactly one configured shortcut."""
    normalized_text = _normalise_text(text)
    return any(_normalise_text(item["shortcut"]) == normalized_text for item in snippets)


def expand_snippets(text: str, snippets: list[dict[str, str]]) -> str:
    """Expand configured shortcuts in a transcript."""
    expanded = text
    for snippet in sorted(snippets, key=lambda item: len(_normalise_text(item["shortcut"])), reverse=True):
        if _normalise_text(snippet["shortcut"]) != _normalise_text(text):
            continue
        expanded = snippet["text"]
        break
    return expanded
