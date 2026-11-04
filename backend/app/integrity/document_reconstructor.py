"""Document reconstructor that replays Monaco document deltas
and verifies the resulting text against the submitted candidate code.
"""

import hashlib
from typing import Any, Dict, List, Tuple


def compute_code_hash(code: str) -> str:
    """Normalize whitespace and compute SHA256 of code string."""
    normalized = "\n".join(line.rstrip() for line in (code or "").splitlines()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def reconstruct_document_from_deltas(
    initial_text: str,
    events: List[Dict[str, Any]],
) -> Tuple[str, bool, List[str]]:
    """Replay document edit deltas to reconstruct final document state.

    Returns:
        (reconstructed_text, had_errors, error_notes)
    """
    doc = initial_text or ""
    had_errors = False
    error_notes: List[str] = []

    # Sort events by timestamp if available
    content_events = [
        e for e in events
        if e.get("type") in {"content_change", "paste", "key_down"} and "inserted_text" in e
    ]
    content_events.sort(key=lambda x: x.get("timestamp", 0))

    for ev in content_events:
        inserted = ev.get("inserted_text")
        if inserted is None:
            continue

        offset = ev.get("range_offset")
        length = ev.get("range_length", 0)

        if offset is None:
            # If no offset specified, assume append or replacement
            doc += inserted
            continue

        if offset < 0 or offset > len(doc):
            had_errors = True
            error_notes.append(f"Offset {offset} out of bounds for doc len {len(doc)}")
            # Clamp to bounds to allow best-effort replay
            offset = max(0, min(offset, len(doc)))

        replace_end = min(len(doc), offset + length)
        doc = doc[:offset] + inserted + doc[replace_end:]

    return doc, had_errors, error_notes


def verify_reconstructed_code(
    reconstructed_code: str,
    submitted_code: str,
) -> Tuple[bool, str, str]:
    """Compare hash of reconstructed code with submitted code.

    Returns:
        (is_match, reconstructed_hash, submitted_hash)
    """
    rec_hash = compute_code_hash(reconstructed_code)
    sub_hash = compute_code_hash(submitted_code)
    is_match = (rec_hash == sub_hash)
    return is_match, rec_hash, sub_hash
