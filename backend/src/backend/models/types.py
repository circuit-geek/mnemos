from enum import Enum
from typing import Any

from sqlalchemy import JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on PostgreSQL; plain JSON elsewhere (unit tests run on SQLite).
JSONType = JSON().with_variant(JSONB(), "postgresql")


def string_enum(enum_cls: type[Enum], **kwargs: Any) -> SAEnum:
    """Store enum values (e.g. "queued") as VARCHAR, avoiding native PG enum migrations."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        **kwargs,
    )
