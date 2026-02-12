"""BLE transport layer for BigHeads using bleak.

The manager acts as a BLE central:
- Scans for devices advertising the BigHeads service UUID.
- Connects to up to max_connections devices.
- Subscribes to notify characteristic for incoming bytes.
- Sends bytes over write characteristic.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from config import NOTIFY_CHAR_UUID, SERVICE_UUID, WRITE_CHAR_UUID

logger = logging.getLogger(__name__)

PacketCallback = Callable[[str, bytes], Awaitable[None]]
PeerCallback = Callable[[dict[str, "PeerState"]], Awaitable[None]]


@dataclass(slots=True)
class PeerState:
    address: str
    name: str
    connected: bool
    last_seen: float


class BLEManager:
    def __init__(
        self,
        node_id: str,
        scan_interval: float,
        scan_window: float,
        max_connections: int,
        on_packet: PacketCallback,
        on_peers_changed: PeerCallback,
    ) -> None:
        self.node_id = node_id
        self.scan_interval = scan_interval
        self.scan_window = scan_window
        self.max_connections = max_connections
        self.on_packet = on_packet
        self.on_peers_changed = on_peers_changed

        self._running = False
        self._scan_task: asyncio.Task[None] | None = None
        self._peers: dict[str, PeerState] = {}
        self._clients: dict[str, BleakClient] = {}
        self._connect_locks: dict[str, asyncio.Lock] = {}
        self._write_lock = asyncio.Lock()

    @property
    def connected_addresses(self) -> list[str]:
        return [addr for addr, c in self._clients.items() if c.is_connected]

    async def start(self) -> None:
        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop(), name="ble-scan-loop")

    async def stop(self) -> None:
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scan_task
        for addr in list(self._clients):
            await self._disconnect(addr)

    async def send_to_all(self, packet: bytes) -> None:
        """Write packet to all connected peers."""
        if not packet:
            return
        async with self._write_lock:
            for addr, client in list(self._clients.items()):
                if not client.is_connected:
                    continue
                try:
                    await client.write_gatt_char(WRITE_CHAR_UUID, packet, response=False)
                except BleakError as exc:
                    logger.warning("Write failed %s: %s", addr, exc)
                    await self._disconnect(addr)

    async def send_to(self, address: str, packet: bytes) -> bool:
        client = self._clients.get(address)
        if client is None or not client.is_connected:
            return False
        try:
            await client.write_gatt_char(WRITE_CHAR_UUID, packet, response=False)
            return True
        except BleakError as exc:
            logger.warning("Write failed to %s: %s", address, exc)
            await self._disconnect(address)
            return False

    async def _scan_loop(self) -> None:
        while self._running:
            try:
                devices = await BleakScanner.discover(timeout=self.scan_window, return_adv=True)
                await self._handle_scan_results(devices)
            except BleakError as exc:
                logger.error(
                    "BLE scan failed. Check Bluetooth permissions/state. Error: %s",
                    exc,
                )
            except Exception as exc:  # defensive fallback for backend-specific errors
                logger.exception("Unexpected scan error: %s", exc)

            await asyncio.sleep(max(0.5, self.scan_interval))

    async def _handle_scan_results(self, results: dict[str, tuple[BLEDevice, Any]]) -> None:
        now = asyncio.get_running_loop().time()
        candidates: list[BLEDevice] = []
        for _, (device, adv) in results.items():
            uuids = {u.lower() for u in (adv.service_uuids or [])}
            if SERVICE_UUID.lower() in uuids:
                self._peers[device.address] = PeerState(
                    address=device.address,
                    name=device.name or adv.local_name or "BigHeads Node",
                    connected=device.address in self.connected_addresses,
                    last_seen=now,
                )
                candidates.append(device)

        await self.on_peers_changed(self._peers)

        connected = len(self.connected_addresses)
        slots = max(0, self.max_connections - connected)
        if slots <= 0:
            return

        for device in candidates:
            if slots <= 0:
                break
            if device.address in self._clients and self._clients[device.address].is_connected:
                continue
            ok = await self._connect(device)
            if ok:
                slots -= 1

    async def _connect(self, device: BLEDevice) -> bool:
        lock = self._connect_locks.setdefault(device.address, asyncio.Lock())
        async with lock:
            existing = self._clients.get(device.address)
            if existing and existing.is_connected:
                return True

            client = BleakClient(device, timeout=10.0)
            try:
                await client.connect()
                await client.start_notify(NOTIFY_CHAR_UUID, self._notification_handler(device.address))
                self._clients[device.address] = client
                if device.address in self._peers:
                    self._peers[device.address].connected = True
                await self.on_peers_changed(self._peers)
                logger.info("Connected BLE peer: %s", device.address)
                return True
            except BleakError as exc:
                logger.warning("Connect failed %s: %s", device.address, exc)
                with contextlib.suppress(Exception):
                    await client.disconnect()
                return False
            except Exception:
                with contextlib.suppress(Exception):
                    await client.disconnect()
                logger.exception("Unexpected BLE connect failure for %s", device.address)
                return False

    def _notification_handler(self, address: str) -> Callable[[Any, bytearray], Awaitable[None]]:
        async def _handler(_: Any, data: bytearray) -> None:
            await self.on_packet(address, bytes(data))

        return _handler

    async def _disconnect(self, address: str) -> None:
        client = self._clients.pop(address, None)
        if client:
            with contextlib.suppress(Exception):
                await client.disconnect()

        peer = self._peers.get(address)
        if peer:
            peer.connected = False

        await self.on_peers_changed(self._peers)
