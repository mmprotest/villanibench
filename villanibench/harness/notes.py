from __future__ import annotations


def append_note(existing: str | None, note: str | None, limit: int = 2000) -> str | None:
    if not note:
        return existing
    clean_note = note.strip()
    if not clean_note:
        return existing
    if not existing:
        return clean_note[:limit]
    combined = existing.rstrip() + "\n" + clean_note
    return combined[:limit]
