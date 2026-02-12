"""Runtime configuration for BigHeads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from utils.helpers import ensure_dir, short_node_id

APP_NAME = "BigHeads"
SERVICE_UUID = "4fdb7f0a-96e4-4ecf-8d2b-6f57494701a1"
WRITE_CHAR_UUID = "4fdb7f0b-96e4-4ecf-8d2b-6f57494701a1"
NOTIFY_CHAR_UUID = "4fdb7f0c-96e4-4ecf-8d2b-6f57494701a1"
APP_DIR = ensure_dir(Path.home() / ".bigheads")
DB_PATH = APP_DIR / "bigheads.db"
CONFIG_PATH = APP_DIR / "config.json"
EXPORT_DIR = ensure_dir(APP_DIR / "exports")


@dataclass(slots=True)
class AppConfig:
    node_id: str = short_node_id()
    ttl_default: int = 12
    scan_interval_sec: float = 7.0
    scan_window_sec: float = 4.0
    max_connections: int = 8
    packet_size_limit: int = 380
    seen_lru_limit: int = 50000
    group_passphrase: str = "change-me"
    auto_theme: bool = True
    theme_mode: str = "system"  # system|light|dark
    autosave_sec: int = 30
    max_inline_file_bytes: int = 2 * 1024 * 1024

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_PATH.exists():
            try:
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                return cls(**raw)
            except (OSError, ValueError, TypeError):
                pass
        cfg = cls()
        cfg.save()
        return cfg

    def save(self) -> None:
        payload = asdict(self)
        CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
