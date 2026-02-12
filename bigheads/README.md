# BigHeads

BigHeads is an offline, decentralized Bluetooth LE mesh messenger prototype for desktop (Windows, macOS, Linux).

It uses:
- `bleak` for BLE scanning/connect/write/notify
- `asyncio` + background runtime thread
- Flooding mesh protocol with TTL/hop and seen-message dedupe
- SQLite persistence (`aiosqlite`)
- E2EE with X25519 + ChaCha20-Poly1305 (`cryptography`)
- `customtkinter` UI

## Features Implemented

- Flooding mesh envelopes with TTL/hop, UUID msg IDs, seen-LRU in SQLite (50,000)
- Broadcast + private chat tabs
- Private chat key establishment with Noise NN-style handshake (`noise_init`/`noise_resp`)
- Group key encryption for broadcast
- File/image transfer (< 2MB) with base64 chunk payloads
- Auto reconnect scanning + connection pool (`max_connections`)
- Routing table persistence (simple next-hop bookkeeping)
- Search in current chat
- Reactions + typing indicator events
- Offline outbox queue (flush when peer returns)
- Block/unblock support in data layer
- Command palette (`Ctrl+K`) for export/copy actions
- JSON/HTML chat export
- Autosave every 30 seconds and graceful shutdown

## Project Layout

```text
bigheads/
├── main.py
├── requirements.txt
├── README.md
├── config.py
├── database.py
├── crypto.py
├── ble_manager.py
├── mesh_protocol.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── chat_tab.py
│   ├── sidebar.py
│   └── components/
├── utils/
│   └── helpers.py
└── assets/
```

## Install

1. Create venv and install dependencies:

```bash
cd bigheads
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Run:

```bash
python main.py
```

## BLE Permissions / OS Notes

### Windows 10/11
- Turn Bluetooth on.
- Enable Location services (BLE scans can require this).
- Allow Python/terminal app Bluetooth access in Privacy settings.

### macOS
- System Settings > Privacy & Security > Bluetooth: allow Terminal/iTerm/Python app.
- First launch may prompt for Bluetooth permission.

### Linux (BlueZ)
- Install and run BlueZ (`bluetoothd`).
- Ensure user has permission for DBus/Bluetooth operations.
- Some distros require running in `bluetooth` group or custom udev policy.

## Build Standalone Executables (PyInstaller)

Run from `bigheads/`:

### Windows
```bash
pyinstaller --noconfirm --onefile --windowed --name BigHeads main.py
```

### macOS
```bash
pyinstaller --noconfirm --onefile --windowed --name BigHeads main.py
```

### Linux
```bash
pyinstaller --noconfirm --onefile --windowed --name BigHeads main.py
```

Artifacts are in `dist/`.

## Test with 3+ Computers

1. On each device, run BigHeads and keep Bluetooth enabled.
2. In settings, set same group passphrase for broadcast.
3. Wait for devices to discover each other in sidebar.
4. Send broadcast text from node A, verify it appears on B and C.
5. Start private chat A->B (first message triggers handshake), then exchange private messages.
6. Disconnect B (close app), send B-directed message from A, reconnect B, verify outbox flush.
7. Transfer image/file < 2MB and verify all chunks appear.

## Security Model

- All regular chat payloads are encrypted:
  - Broadcast: shared group key derived from configured passphrase.
  - Private: X25519 session bootstrap + per-message derived AEAD key.
- Integrity: ChaCha20-Poly1305 authentication tag.
- Replay-loop resistance: persistent seen message IDs + TTL.

## Security Limitations (Prototype)

- Handshake identity is unauthenticated (NN-style, vulnerable to MITM).
- No formal double-ratchet yet; forward secrecy is partial, not full deniability-grade.
- BLE transport authentication depends on OS stack/device behavior.
- File transfer uses base64 in-message chunks, not stream protocol.

## Tunable Parameters

Edit `config.py` defaults or use Settings UI:
- `ttl_default`
- `scan_interval_sec`
- `max_connections`
- `group_passphrase`
- `packet_size_limit`
- `seen_lru_limit`
- `max_inline_file_bytes`

## TODO (Next Improvements)

1. Replace NN prototype with full Noise IK/XX patterns + identity verification UX.
2. Add proper ratcheting for stronger forward secrecy and post-compromise security.
3. Add robust chunk reassembly with retransmit/ACK for large files.
4. Support BLE MTU negotiation and adaptive packetization.
5. Add richer route scoring (latency/link quality) and optional DHT metadata exchange.
6. Add explicit block/unblock UI controls and moderation logs.
7. Add presence heartbeat aging + better offline/online transitions.
8. Add Wi-Fi LAN mesh transport plugin.
9. Add mobile clients (Android/iOS) with shared protocol core.
10. Add automated integration test harness with 3+ virtual nodes.

## Roadmap

- v0.2: Better routing + reliable chunk transport
- v0.3: Strong authenticated key exchange + ratchet
- v0.4: Multi-transport mesh (BLE + Wi-Fi)
- v0.5: Mobile companion apps
