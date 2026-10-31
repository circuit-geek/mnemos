"""Validation of user-supplied concepts (what to track in one video)."""

import re

from backend.core.exceptions import InvalidVideoError

MAX_CONCEPTS = 8
# Letters, digits, spaces, hyphens, apostrophes; must start with a letter or digit.
_CONCEPT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '\-]{0,39}$")


def parse_concepts(raw: str | None) -> list[str] | None:
    """Comma-separated names -> unique cleaned list; None when none were given (use discovery)."""
    if raw is None or not raw.strip():
        return None
    concepts: list[str] = []
    for part in raw.split(","):
        name = " ".join(part.lower().split())
        if not name:
            continue
        if not _CONCEPT.match(name):
            raise InvalidVideoError(
                f"Invalid concept {part.strip()[:40]!r}: use short plain names such as 'mug'"
            )
        if name not in concepts:
            concepts.append(name)
    if len(concepts) > MAX_CONCEPTS:
        raise InvalidVideoError(f"At most {MAX_CONCEPTS} concepts are allowed")
    return concepts or None
