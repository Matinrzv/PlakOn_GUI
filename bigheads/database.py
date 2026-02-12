"""SQLite persistence layer (async) for BigHeads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    """Async SQLite wrapper with app-specific queries."""

    def __init__(self, db_path: Path, seen_limit: int = 50000) -> None:
        self.db_path = db_path
        self.seen_limit = seen_limit
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL;")
        await self.conn.execute("PRAGMA foreign_keys=ON;")
        await self._init_schema()

    async def _init_schema(self) -> None:
        assert self.conn is not None
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                msg_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                msg_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp REAL NOT NULL,
                reply_to TEXT,
                outgoing INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS contacts (
                node_id TEXT PRIMARY KEY,
                alias TEXT,
                last_seen REAL,
                blocked INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS seen_messages (
                msg_id TEXT PRIMARY KEY,
                seen_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS routing (
                target_node TEXT PRIMARY KEY,
                via_node TEXT NOT NULL,
                hops INTEGER NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_keys (
                chat_id TEXT PRIMARY KEY,
                key_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                envelope_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT NOT NULL,
                reactor TEXT NOT NULL,
                reaction TEXT NOT NULL,
                timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS typing_state (
                chat_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                is_typing INTEGER NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.commit()
            await self.conn.close()
            self.conn = None

    async def save_message(self, envelope: dict[str, Any], outgoing: bool) -> None:
        assert self.conn is not None
        chat_id = envelope.get("chat_id") or (envelope["to"] if envelope["to"] != "*" else "broadcast")
        await self.conn.execute(
            """
            INSERT OR REPLACE INTO messages
            (msg_id, chat_id, sender, recipient, msg_type, payload, timestamp, reply_to, outgoing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                envelope["msg_id"],
                chat_id,
                envelope["from"],
                envelope["to"],
                envelope["type"],
                json.dumps(envelope["payload"]),
                envelope["timestamp"],
                envelope.get("reply_to"),
                int(outgoing),
            ),
        )

    async def get_chat_messages(self, chat_id: str, limit: int = 200) -> list[dict[str, Any]]:
        assert self.conn is not None
        cur = await self.conn.execute(
            """
            SELECT * FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in reversed(rows)]

    async def mark_seen(self, msg_id: str, seen_at: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "INSERT OR REPLACE INTO seen_messages (msg_id, seen_at) VALUES (?, ?)",
            (msg_id, seen_at),
        )
        # Keep only newest N IDs using timestamp ordering.
        await self.conn.execute(
            """
            DELETE FROM seen_messages
            WHERE msg_id IN (
                SELECT msg_id FROM seen_messages
                ORDER BY seen_at DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (self.seen_limit,),
        )

    async def has_seen(self, msg_id: str) -> bool:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT 1 FROM seen_messages WHERE msg_id = ?", (msg_id,))
        return (await cur.fetchone()) is not None

    async def upsert_contact(self, node_id: str, last_seen: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            """
            INSERT INTO contacts (node_id, last_seen)
            VALUES (?, ?)
            ON CONFLICT(node_id) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (node_id, last_seen),
        )

    async def list_contacts(self) -> list[dict[str, Any]]:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM contacts ORDER BY COALESCE(last_seen, 0) DESC")
        return [dict(r) for r in await cur.fetchall()]

    async def set_blocked(self, node_id: str, blocked: bool) -> None:
        assert self.conn is not None
        await self.conn.execute(
            """
            INSERT INTO contacts (node_id, blocked)
            VALUES (?, ?)
            ON CONFLICT(node_id) DO UPDATE SET blocked = excluded.blocked
            """,
            (node_id, int(blocked)),
        )

    async def is_blocked(self, node_id: str) -> bool:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT blocked FROM contacts WHERE node_id = ?",
            (node_id,),
        )
        row = await cur.fetchone()
        return bool(row["blocked"]) if row else False

    async def update_route(self, target: str, via: str, hops: int, ts: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            """
            INSERT INTO routing (target_node, via_node, hops, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(target_node) DO UPDATE SET
              via_node = excluded.via_node,
              hops = excluded.hops,
              updated_at = excluded.updated_at
            """,
            (target, via, hops, ts),
        )

    async def get_route(self, target: str) -> dict[str, Any] | None:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM routing WHERE target_node = ?", (target,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def set_chat_key(self, chat_id: str, key_data: dict[str, Any], ts: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            """
            INSERT INTO chat_keys (chat_id, key_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET key_json = excluded.key_json, updated_at = excluded.updated_at
            """,
            (chat_id, json.dumps(key_data), ts),
        )

    async def get_chat_key(self, chat_id: str) -> dict[str, Any] | None:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT key_json FROM chat_keys WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        return json.loads(row["key_json"]) if row else None

    async def enqueue_outbox(self, recipient: str, envelope: dict[str, Any], ts: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "INSERT INTO outbox (recipient, envelope_json, created_at) VALUES (?, ?, ?)",
            (recipient, json.dumps(envelope), ts),
        )

    async def dequeue_outbox_for(self, recipient: str, limit: int = 100) -> list[tuple[int, dict[str, Any]]]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT id, envelope_json FROM outbox WHERE recipient = ? ORDER BY id ASC LIMIT ?",
            (recipient, limit),
        )
        rows = await cur.fetchall()
        return [(r["id"], json.loads(r["envelope_json"])) for r in rows]

    async def delete_outbox_ids(self, ids: list[int]) -> None:
        assert self.conn is not None
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        await self.conn.execute(f"DELETE FROM outbox WHERE id IN ({placeholders})", ids)

    async def add_reaction(self, msg_id: str, reactor: str, reaction: str, ts: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "INSERT INTO reactions (msg_id, reactor, reaction, timestamp) VALUES (?, ?, ?, ?)",
            (msg_id, reactor, reaction, ts),
        )

    async def get_reactions(self, msg_id: str) -> list[dict[str, Any]]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT reactor, reaction, timestamp FROM reactions WHERE msg_id = ? ORDER BY timestamp ASC",
            (msg_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def set_typing(self, chat_id: str, node_id: str, is_typing: bool, ts: float) -> None:
        assert self.conn is not None
        await self.conn.execute(
            """
            INSERT INTO typing_state (chat_id, node_id, is_typing, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
              node_id = excluded.node_id,
              is_typing = excluded.is_typing,
              updated_at = excluded.updated_at
            """,
            (chat_id, node_id, int(is_typing), ts),
        )

    async def commit(self) -> None:
        assert self.conn is not None
        await self.conn.commit()

    async def export_chat_json(self, chat_id: str) -> list[dict[str, Any]]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp ASC",
            (chat_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def clear_history(self) -> None:
        assert self.conn is not None
        await self.conn.execute("DELETE FROM messages")
        await self.conn.execute("DELETE FROM reactions")
        await self.conn.execute("DELETE FROM typing_state")
