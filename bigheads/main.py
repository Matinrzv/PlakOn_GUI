"""BigHeads desktop app entrypoint."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import queue
import signal
import threading
from pathlib import Path
from typing import Any

from ble_manager import BLEManager
from config import APP_NAME, AppConfig, DB_PATH
from crypto import CryptoManager
from database import Database
from mesh_protocol import MeshProtocol
from ui.main_window import MainWindow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(APP_NAME)


class RuntimeBridge:
    """Runs asyncio services in a background thread and bridges events to UI."""

    def __init__(self, cfg: AppConfig, event_queue: "queue.Queue[dict[str, Any]]") -> None:
        self.cfg = cfg
        self.event_queue = event_queue
        self.loop = asyncio.new_event_loop()
        self.thread: threading.Thread | None = None

        self.db = Database(DB_PATH, seen_limit=cfg.seen_lru_limit)
        self.crypto = CryptoManager(cfg.group_passphrase)
        self.ble = BLEManager(
            node_id=cfg.node_id,
            scan_interval=cfg.scan_interval_sec,
            scan_window=cfg.scan_window_sec,
            max_connections=cfg.max_connections,
            on_packet=self._on_ble_packet,
            on_peers_changed=self._on_peers_changed,
        )
        self.mesh = MeshProtocol(
            node_id=cfg.node_id,
            db=self.db,
            crypto=self.crypto,
            ble=self.ble,
            ui_callback=self._on_mesh_event,
            packet_size_limit=cfg.packet_size_limit,
            default_ttl=cfg.ttl_default,
            max_file_bytes=cfg.max_inline_file_bytes,
        )
        self._autosave_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="bigheads-async-loop")
        self.thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._startup())
        self.loop.run_forever()

    async def _startup(self) -> None:
        await self.db.connect()
        await self.ble.start()
        await self.mesh.start()
        self._autosave_task = asyncio.create_task(self._autosave_loop(), name="autosave-loop")

    async def _autosave_loop(self) -> None:
        while True:
            await asyncio.sleep(max(5, self.cfg.autosave_sec))
            self.cfg.save()
            await self.db.commit()

    async def _on_ble_packet(self, address: str, data: bytes) -> None:
        await self.mesh.handle_ble_packet(address, data)

    async def _on_peers_changed(self, peers: dict[str, Any]) -> None:
        payload: dict[str, Any] = {}
        for addr, st in peers.items():
            payload[addr] = {
                "address": st.address,
                "connected": st.connected,
                "name": st.name,
                "last_seen": st.last_seen,
                "node_id": self.mesh._addr_to_node.get(addr),
            }
        self.event_queue.put({"type": "peers", "peers": payload})

    async def _on_mesh_event(self, event: dict[str, Any]) -> None:
        if event.get("type") == "message":
            env = event.get("env", {})
            msg_type = env.get("type")
            if msg_type in {"text", "image", "file", "system"}:
                self.event_queue.put({"type": "message", "env": env})
        elif event.get("type") == "typing":
            env = event.get("env", {})
            if env.get("payload", {}).get("typing"):
                self.event_queue.put({"type": "toast", "text": f"{env.get('from')} is typing..."})
        elif event.get("type") == "reaction":
            env = event.get("env", {})
            self.event_queue.put({"type": "toast", "text": f"Reaction from {env.get('from')}"})

    def call(self, action: str, args: tuple[Any, ...]) -> None:
        asyncio.run_coroutine_threadsafe(self._dispatch(action, args), self.loop)

    async def _dispatch(self, action: str, args: tuple[Any, ...]) -> None:
        if action == "send_text":
            to, text = args
            await self.mesh.send_text(str(to), str(text))
            await self.db.commit()
            return

        if action == "send_file":
            to, path, as_image = args
            try:
                await self.mesh.send_file(str(to), Path(str(path)), bool(as_image))
                await self.db.commit()
            except Exception as exc:
                self.event_queue.put({"type": "toast", "text": f"File send failed: {exc}"})
            return

        if action == "typing":
            chat_id, to, is_typing = args
            await self.mesh.send_typing(str(chat_id), str(to), bool(is_typing))
            return

        if action == "reaction":
            to, msg_id, reaction = args
            await self.mesh.send_reaction(str(to), str(msg_id), str(reaction))
            await self.db.commit()
            return

        if action == "search":
            chat_id, term = args
            rows = await self.mesh.search_chat(str(chat_id), str(term))
            self.event_queue.put({"type": "search_results", "chat_id": str(chat_id), "rows": rows})
            return

        if action == "load_history":
            chat_id = str(args[0])
            rows = await self.db.get_chat_messages(chat_id)
            self.event_queue.put({"type": "history", "chat_id": chat_id, "rows": rows})
            return

        if action == "export":
            chat_id, fmt = args
            out = await self.mesh.export_chat(str(chat_id), str(fmt))
            self.event_queue.put({"type": "toast", "text": f"Exported: {out}"})
            return

        if action == "reload_config":
            self.cfg = AppConfig.load()
            self.crypto.update_group_passphrase(self.cfg.group_passphrase)
            self.mesh.default_ttl = self.cfg.ttl_default
            self.ble.scan_interval = self.cfg.scan_interval_sec
            self.ble.max_connections = self.cfg.max_connections
            return

        if action == "clear_history":
            await self.db.clear_history()
            await self.db.commit()
            return

    def shutdown(self) -> None:
        fut = asyncio.run_coroutine_threadsafe(self._shutdown_async(), self.loop)
        with contextlib.suppress(Exception):
            fut.result(timeout=8)
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)

    async def _shutdown_async(self) -> None:
        if self._autosave_task:
            self._autosave_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._autosave_task
        self.cfg.save()
        await self.db.commit()
        await self.ble.stop()
        await self.db.close()


def main() -> None:
    cfg = AppConfig.load()
    events: queue.Queue[dict[str, Any]] = queue.Queue()
    runtime = RuntimeBridge(cfg, events)
    runtime.start()

    app = MainWindow(cfg, events)
    app.set_async_call(runtime.call)

    def _shutdown(*_: object) -> None:
        runtime.shutdown()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", _shutdown)
    with contextlib.suppress(ValueError):
        signal.signal(signal.SIGINT, _shutdown)

    app.mainloop()


if __name__ == "__main__":
    main()
