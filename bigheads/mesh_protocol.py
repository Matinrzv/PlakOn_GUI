"""Flooding mesh protocol implementation for BigHeads."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from ble_manager import BLEManager
from config import EXPORT_DIR
from crypto import ChatSession, CryptoManager
from database import Database
from utils.helpers import chunk_bytes, compact_json, from_b64, new_msg_id, safe_json_loads, to_b64, utc_ts

logger = logging.getLogger(__name__)

UiEventCallback = Callable[[dict[str, Any]], Awaitable[None]]


class MeshProtocol:
    """Application-level mesh message handling with BLE transport."""

    def __init__(
        self,
        node_id: str,
        db: Database,
        crypto: CryptoManager,
        ble: BLEManager,
        ui_callback: UiEventCallback,
        packet_size_limit: int = 380,
        default_ttl: int = 12,
        max_file_bytes: int = 2 * 1024 * 1024,
    ) -> None:
        self.node_id = node_id
        self.db = db
        self.crypto = crypto
        self.ble = ble
        self.ui_callback = ui_callback
        self.packet_size_limit = packet_size_limit
        self.default_ttl = default_ttl
        self.max_file_bytes = max_file_bytes

        self._chat_sessions: dict[str, ChatSession] = {}
        self._pending_noise: dict[str, Any] = {}
        self._addr_to_node: dict[str, str] = {}
        self._node_to_addr: dict[str, str] = {}
        self._fragments: dict[str, dict[int, str]] = defaultdict(dict)
        self._fragment_meta: dict[str, tuple[int, str]] = {}
        self._hello_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await self._load_sessions()
        self._hello_task = asyncio.create_task(self._hello_loop(), name="mesh-hello-loop")

    async def stop(self) -> None:
        if self._hello_task:
            self._hello_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._hello_task

    async def _load_sessions(self) -> None:
        contacts = await self.db.list_contacts()
        for contact in contacts:
            chat_id = contact["node_id"]
            stored = await self.db.get_chat_key(chat_id)
            if stored:
                self._chat_sessions[chat_id] = self.crypto.session_from_dict(stored)

    async def _hello_loop(self) -> None:
        while True:
            try:
                await self.send_system(
                    to="*",
                    payload={"kind": "hello", "node_id": self.node_id, "ts": utc_ts()},
                    encrypted=True,
                )
            except Exception as exc:
                logger.debug("hello send failed: %s", exc)
            await asyncio.sleep(15)

    async def handle_ble_packet(self, address: str, raw: bytes) -> None:
        packet = safe_json_loads(raw)
        if not packet:
            return

        if packet.get("kind") == "frag":
            assembled = self._collect_fragment(packet, address)
            if assembled is None:
                return
            packet = safe_json_loads(assembled)
            if not packet:
                return

        if packet.get("kind") != "mesh":
            return

        env = packet.get("env")
        if not isinstance(env, dict):
            return

        await self._process_envelope(env, incoming_addr=address)

    def _collect_fragment(self, frag: dict[str, Any], address: str) -> bytes | None:
        frame_id = frag.get("frame_id")
        if not frame_id:
            return None
        total = int(frag.get("total", 0))
        idx = int(frag.get("idx", 0))
        data = frag.get("data")
        if total <= 0 or idx < 0 or idx >= total or not isinstance(data, str):
            return None

        key = f"{address}:{frame_id}"
        self._fragments[key][idx] = data
        self._fragment_meta[key] = (total, frame_id)
        if len(self._fragments[key]) < total:
            return None

        joined = "".join(self._fragments[key][i] for i in range(total))
        del self._fragments[key]
        self._fragment_meta.pop(key, None)
        return from_b64(joined)

    async def _process_envelope(self, env: dict[str, Any], incoming_addr: str | None) -> None:
        msg_id = env.get("msg_id")
        sender = env.get("from")
        if not isinstance(msg_id, str) or not isinstance(sender, str):
            return

        if await self.db.has_seen(msg_id):
            return
        await self.db.mark_seen(msg_id, utc_ts())

        if incoming_addr:
            self._addr_to_node[incoming_addr] = sender
            self._node_to_addr[sender] = incoming_addr
            await self.db.update_route(target=sender, via=sender, hops=int(env.get("hop", 0)) + 1, ts=utc_ts())
            await self.db.upsert_contact(sender, utc_ts())

        if await self.db.is_blocked(sender):
            return

        plaintext_env = await self._decrypt_envelope(env)
        if plaintext_env is None:
            return

        # Save message if user-visible payload.
        target = plaintext_env.get("to")
        is_visible = target == "*" or target == self.node_id
        if is_visible and plaintext_env.get("type") in {"text", "file", "image", "system"}:
            chat_id = "broadcast" if target == "*" else sender
            await self.db.save_message({**plaintext_env, "chat_id": chat_id}, outgoing=False)

        if is_visible:
            await self._dispatch_message(plaintext_env)
        await self._forward_if_needed(env, incoming_addr)

    async def _decrypt_envelope(self, env: dict[str, Any]) -> dict[str, Any] | None:
        # System handshake init/resp may be plaintext because no session exists yet.
        enc = env.get("enc", "group")
        try:
            if enc == "none":
                payload = env["payload"]
            elif enc == "group":
                plaintext = self.crypto.decrypt_group(env["payload"], aad=env["msg_id"].encode("utf-8"))
                payload = json.loads(plaintext.decode("utf-8"))
            elif enc == "private":
                chat_id = env["from"] if env["from"] != self.node_id else env["to"]
                session = self._chat_sessions.get(chat_id)
                if not session:
                    logger.warning("No session for private chat %s", chat_id)
                    return None
                plaintext = self.crypto.decrypt_private(
                    env["payload"],
                    chat_id=chat_id,
                    msg_id=env["msg_id"],
                    session=session,
                    aad=env["msg_id"].encode("utf-8"),
                )
                payload = json.loads(plaintext.decode("utf-8"))
            else:
                return None
        except Exception as exc:
            logger.warning("decrypt failed: %s", exc)
            return None

        out = dict(env)
        out["payload"] = payload
        return out

    async def _dispatch_message(self, env: dict[str, Any]) -> None:
        msg_type = env.get("type")
        payload = env.get("payload")

        if msg_type == "system" and isinstance(payload, dict):
            kind = payload.get("kind")
            if kind == "hello":
                await self.ui_callback({"type": "peer_hello", "node_id": env["from"], "timestamp": env["timestamp"]})
                await self._flush_outbox_for(env["from"])
            elif kind == "noise_init":
                await self._on_noise_init(env)
            elif kind == "noise_resp":
                await self._on_noise_resp(env)
            elif kind == "reaction":
                await self.db.add_reaction(env.get("reply_to", ""), env["from"], payload.get("reaction", ""), utc_ts())
                await self.ui_callback({"type": "reaction", "env": env})
            elif kind == "typing":
                await self.db.set_typing(payload.get("chat_id", ""), env["from"], bool(payload.get("typing", False)), utc_ts())
                await self.ui_callback({"type": "typing", "env": env})

        await self.ui_callback({"type": "message", "env": env})

    async def _forward_if_needed(self, original_env: dict[str, Any], incoming_addr: str | None) -> None:
        ttl = int(original_env.get("ttl", 0))
        if ttl <= 0:
            return

        target = original_env.get("to")
        # Do not forward if this direct message is for me.
        if target == self.node_id:
            return

        fwd = dict(original_env)
        fwd["ttl"] = ttl - 1
        fwd["hop"] = int(original_env.get("hop", 0)) + 1
        if fwd["ttl"] <= 0:
            return

        await self._send_envelope_raw(fwd, exclude_addr=incoming_addr)

    async def send_text(self, to: str, text: str, reply_to: str | None = None) -> dict[str, Any]:
        return await self._send_payload(to=to, msg_type="text", payload=text, reply_to=reply_to)

    async def send_typing(self, chat_id: str, to: str, is_typing: bool) -> None:
        await self.send_system(
            to=to,
            payload={"kind": "typing", "chat_id": chat_id, "typing": is_typing},
            encrypted=(to == "*"),
        )

    async def send_reaction(self, to: str, msg_id: str, reaction: str) -> None:
        await self._send_payload(
            to=to,
            msg_type="system",
            payload={"kind": "reaction", "reaction": reaction},
            reply_to=msg_id,
        )

    async def send_system(self, to: str, payload: dict[str, Any], encrypted: bool = True) -> dict[str, Any]:
        return await self._send_payload(to=to, msg_type="system", payload=payload, encrypted=encrypted)

    async def send_file(self, to: str, file_path: Path, as_image: bool = False) -> list[dict[str, Any]]:
        data = file_path.read_bytes()
        if len(data) > self.max_file_bytes:
            raise ValueError(f"File too large ({len(data)} bytes), limit is {self.max_file_bytes}")

        chunk_payload_bytes = max(64, self.packet_size_limit * 2)
        parts = chunk_bytes(data, chunk_payload_bytes)
        envelopes = []
        for i, part in enumerate(parts):
            payload = {
                "name": file_path.name,
                "mime": "image" if as_image else "file",
                "chunk_index": i,
                "chunk_total": len(parts),
                "data": to_b64(part),
            }
            env = await self._send_payload(to=to, msg_type="image" if as_image else "file", payload=payload)
            envelopes.append(env)
        return envelopes

    async def start_private_chat(self, peer_node_id: str) -> None:
        pub_b64, init_priv = self.crypto.start_noise_nn()
        self._pending_noise[peer_node_id] = init_priv
        await self.send_system(
            to=peer_node_id,
            payload={"kind": "noise_init", "pub": pub_b64},
            encrypted=False,
        )

    async def _on_noise_init(self, env: dict[str, Any]) -> None:
        payload = env.get("payload", {})
        init_pub = payload.get("pub")
        if not isinstance(init_pub, str):
            return
        resp_payload, session = self.crypto.respond_noise_nn(init_pub)
        chat_id = env["from"]
        self._chat_sessions[chat_id] = session
        await self.db.set_chat_key(chat_id, self.crypto.session_to_dict(session), utc_ts())
        await self.send_system(to=chat_id, payload={"kind": "noise_resp", "pub": resp_payload["pub"]}, encrypted=False)

    async def _on_noise_resp(self, env: dict[str, Any]) -> None:
        chat_id = env["from"]
        init_priv = self._pending_noise.pop(chat_id, None)
        if init_priv is None:
            return
        resp_pub = env.get("payload", {}).get("pub")
        if not isinstance(resp_pub, str):
            return
        session = self.crypto.finalize_noise_nn(init_priv, resp_pub)
        self._chat_sessions[chat_id] = session
        await self.db.set_chat_key(chat_id, self.crypto.session_to_dict(session), utc_ts())

    async def _send_payload(
        self,
        to: str,
        msg_type: str,
        payload: Any,
        reply_to: str | None = None,
        encrypted: bool | None = None,
    ) -> dict[str, Any]:
        envelope: dict[str, Any] = {
            "msg_id": new_msg_id(),
            "from": self.node_id,
            "to": to,
            "ttl": self.default_ttl,
            "hop": 0,
            "timestamp": utc_ts(),
            "type": msg_type,
            "payload": payload,
            "reply_to": reply_to,
        }

        should_encrypt = encrypted if encrypted is not None else True
        if not should_encrypt:
            envelope["enc"] = "none"
        elif to == "*":
            envelope["enc"] = "group"
            ct = self.crypto.encrypt_group(
                compact_json(payload if isinstance(payload, dict) else {"text": payload}),
                aad=envelope["msg_id"].encode("utf-8"),
            )
            envelope["payload"] = ct
        else:
            envelope["enc"] = "private"
            session = self._chat_sessions.get(to)
            if not session:
                await self.start_private_chat(to)
                await self.db.enqueue_outbox(to, envelope, utc_ts())
                await self.db.commit()
                return envelope
            ct = self.crypto.encrypt_private(
                compact_json(payload if isinstance(payload, dict) else {"text": payload}),
                chat_id=to,
                msg_id=envelope["msg_id"],
                session=session,
                aad=envelope["msg_id"].encode("utf-8"),
            )
            envelope["payload"] = ct

        await self.db.save_message(
            {
                **envelope,
                "chat_id": "broadcast" if to == "*" else to,
                "payload": payload,
            },
            outgoing=True,
        )
        await self._send_envelope_raw(envelope)
        return envelope

    async def _send_envelope_raw(self, envelope: dict[str, Any], exclude_addr: str | None = None) -> None:
        outer = {"kind": "mesh", "env": envelope}
        raw = compact_json(outer)

        # Frame directly if packet fits.
        if len(raw) <= self.packet_size_limit:
            await self._send_frame(raw, envelope, exclude_addr)
            return

        frame_id = new_msg_id()
        b64 = to_b64(raw)
        # Keep fragment JSON safely below packet limit.
        chunk_len = max(30, self.packet_size_limit - 140)
        chunks = [b64[i : i + chunk_len] for i in range(0, len(b64), chunk_len)]
        for idx, chunk in enumerate(chunks):
            frag = {"kind": "frag", "frame_id": frame_id, "idx": idx, "total": len(chunks), "data": chunk}
            await self._send_frame(compact_json(frag), envelope, exclude_addr)

    async def _send_frame(self, frame: bytes, envelope: dict[str, Any], exclude_addr: str | None) -> None:
        to = envelope.get("to")
        if to not in {"*", self.node_id}:
            route = await self.db.get_route(to)
            via_node = route["via_node"] if route else None
            addr = self._node_to_addr.get(via_node or "") or self._node_to_addr.get(to)
            if addr:
                if addr != exclude_addr and await self.ble.send_to(addr, frame):
                    return
                await self.db.enqueue_outbox(to, envelope, utc_ts())
                return
            await self.db.enqueue_outbox(to, envelope, utc_ts())
            return

        # Broadcast floods all connected peers.
        if exclude_addr:
            for addr in self.ble.connected_addresses:
                if addr == exclude_addr:
                    continue
                await self.ble.send_to(addr, frame)
        else:
            await self.ble.send_to_all(frame)

    async def _flush_outbox_for(self, node_id: str) -> None:
        pending = await self.db.dequeue_outbox_for(node_id)
        if not pending:
            return
        delete_ids: list[int] = []
        for row_id, env in pending:
            await self._send_envelope_raw(env)
            delete_ids.append(row_id)
        await self.db.delete_outbox_ids(delete_ids)

    async def search_chat(self, chat_id: str, term: str) -> list[dict[str, Any]]:
        all_msgs = await self.db.get_chat_messages(chat_id, limit=500)
        if not term.strip():
            return all_msgs
        needle = term.lower()
        out = []
        for row in all_msgs:
            payload = row.get("payload", "")
            if isinstance(payload, str):
                text = payload
            else:
                text = json.dumps(payload)
            if needle in text.lower():
                out.append(row)
        return out

    async def export_chat(self, chat_id: str, fmt: str = "json") -> Path:
        rows = await self.db.export_chat_json(chat_id)
        ts = int(utc_ts())
        if fmt == "json":
            out_path = EXPORT_DIR / f"{chat_id}-{ts}.json"
            out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
            return out_path

        out_path = EXPORT_DIR / f"{chat_id}-{ts}.html"
        html = ["<html><body><h1>BigHeads Export</h1><ul>"]
        for row in rows:
            html.append(
                f"<li><b>{row['sender']}</b> [{row['timestamp']:.3f}] : {row['payload']}</li>"
            )
        html.append("</ul></body></html>")
        out_path.write_text("\n".join(html), encoding="utf-8")
        return out_path
