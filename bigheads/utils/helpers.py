"""Shared utility helpers for BigHeads."""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any


def utc_ts() -> float:
    """Return the current unix timestamp as float seconds."""
    return time.time()


def short_node_id(seed: str | None = None) -> str:
    """Generate a stable-ish 8-char node id from seed or random UUID."""
    raw = seed or str(uuid.uuid4())
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:8]


def new_msg_id() -> str:
    """Return a UUID4 string for message IDs."""
    return str(uuid.uuid4())


def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def from_b64(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def compact_json(data: dict[str, Any]) -> bytes:
    """Compact UTF-8 JSON encoding."""
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def safe_json_loads(raw: bytes | str) -> dict[str, Any] | None:
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def chunk_bytes(data: bytes, chunk_size: int) -> list[bytes]:
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
