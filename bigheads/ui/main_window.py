"""Main app window for BigHeads."""

from __future__ import annotations

import json
import queue
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
import pyperclip

from config import AppConfig
from ui.chat_tab import ChatTab
from ui.sidebar import Sidebar

AsyncCall = Callable[[str, tuple], None]


class MainWindow(ctk.CTk):
    def __init__(self, cfg: AppConfig, event_queue: "queue.Queue[dict]") -> None:
        super().__init__()
        self.cfg = cfg
        self.event_queue = event_queue
        self.async_call: AsyncCall | None = None

        self.title(f"BigHeads - {cfg.node_id}")
        self.geometry("1180x760")
        self.minsize(980, 620)

        mode = "System" if cfg.theme_mode == "system" else cfg.theme_mode.capitalize()
        ctk.set_appearance_mode(mode)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self.select_chat, self.open_settings)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        self.main_stack = ctk.CTkFrame(self, fg_color="transparent")
        self.main_stack.grid(row=0, column=1, sticky="nsew")
        self.main_stack.grid_columnconfigure(0, weight=1)
        self.main_stack.grid_rowconfigure(0, weight=1)

        self.tabs: dict[str, ChatTab] = {}
        self.active_chat = "broadcast"
        self._ensure_tab("broadcast")
        self.select_chat("broadcast")

        self.bind("<Control-k>", lambda _: self.open_command_palette())

        self.after(120, self._poll_events)

    def set_async_call(self, fn: AsyncCall) -> None:
        self.async_call = fn

    def _ensure_tab(self, chat_id: str) -> ChatTab:
        tab = self.tabs.get(chat_id)
        if tab:
            return tab
        tab = ChatTab(
            self.main_stack,
            chat_id=chat_id,
            local_node_id=self.cfg.node_id,
            on_send_text=self._send_text,
            on_send_file=self._send_file,
            on_search=self._search,
            on_typing=self._typing,
            on_reaction=self._reaction,
        )
        self.tabs[chat_id] = tab
        return tab

    def select_chat(self, chat_id: str) -> None:
        self.active_chat = chat_id
        tab = self._ensure_tab(chat_id)
        for t in self.tabs.values():
            t.grid_forget()
        tab.grid(row=0, column=0, sticky="nsew")
        self._load_history(chat_id)

    def _load_history(self, chat_id: str) -> None:
        if self.async_call:
            self.async_call("load_history", (chat_id,))

    def _send_text(self, chat_id: str, text: str) -> None:
        to = "*" if chat_id == "broadcast" else chat_id
        if self.async_call:
            self.async_call("send_text", (to, text))

    def _send_file(self, chat_id: str, path: Path, as_image: bool) -> None:
        to = "*" if chat_id == "broadcast" else chat_id
        if self.async_call:
            self.async_call("send_file", (to, str(path), as_image))

    def _search(self, chat_id: str, term: str) -> None:
        if self.async_call:
            self.async_call("search", (chat_id, term))

    def _typing(self, chat_id: str, is_typing: bool) -> None:
        to = "*" if chat_id == "broadcast" else chat_id
        if self.async_call:
            self.async_call("typing", (chat_id, to, is_typing))

    def _reaction(self, chat_id: str, msg_id: str, reaction: str) -> None:
        to = "*" if chat_id == "broadcast" else chat_id
        if self.async_call:
            self.async_call("reaction", (to, msg_id, reaction))

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)

        self.after(120, self._poll_events)

    def _handle_event(self, event: dict) -> None:
        et = event.get("type")
        if et == "peers":
            peers: dict = event.get("peers", {})
            online = sum(1 for v in peers.values() if v.get("connected"))
            ids = sorted({v.get("node_id") for v in peers.values() if v.get("node_id")})
            self.sidebar.update_online(online)
            self.sidebar.set_contacts(ids)
            return

        if et == "message":
            env = event.get("env", {})
            chat_id = "broadcast" if env.get("to") == "*" else (env.get("from") if env.get("from") != self.cfg.node_id else env.get("to"))
            tab = self._ensure_tab(str(chat_id))
            tab.add_message(env)
            return

        if et == "history":
            chat_id = str(event.get("chat_id"))
            tab = self._ensure_tab(chat_id)
            tab.clear_messages()
            for row in event.get("rows", []):
                payload = row.get("payload")
                try:
                    payload_obj = json.loads(payload) if isinstance(payload, str) else payload
                except json.JSONDecodeError:
                    payload_obj = payload
                env = {
                    "msg_id": row.get("msg_id"),
                    "from": row.get("sender"),
                    "to": row.get("recipient"),
                    "type": row.get("msg_type"),
                    "timestamp": row.get("timestamp"),
                    "payload": payload_obj,
                }
                tab.add_message(env)
            return

        if et == "search_results":
            chat_id = str(event.get("chat_id"))
            tab = self._ensure_tab(chat_id)
            tab.clear_messages()
            for row in event.get("rows", []):
                payload = row.get("payload")
                env = {
                    "msg_id": row.get("msg_id"),
                    "from": row.get("sender"),
                    "to": row.get("recipient"),
                    "type": row.get("msg_type"),
                    "timestamp": row.get("timestamp"),
                    "payload": payload,
                }
                tab.add_message(env)
            return

        if et == "toast":
            self._toast(str(event.get("text", "")))

    def _toast(self, text: str) -> None:
        top = ctk.CTkToplevel(self)
        top.title("BigHeads")
        top.geometry("360x90")
        label = ctk.CTkLabel(top, text=text, wraplength=330)
        label.pack(expand=True, fill="both", padx=12, pady=12)
        top.after(2200, top.destroy)

    def open_command_palette(self) -> None:
        palette = ctk.CTkToplevel(self)
        palette.title("Command Palette")
        palette.geometry("440x260")
        palette.grab_set()

        ctk.CTkLabel(palette, text="Command", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(12, 4))
        cmd_entry = ctk.CTkEntry(palette, placeholder_text="export json | export html | copy node | clear chat")
        cmd_entry.pack(fill="x", padx=12, pady=8)

        def run_cmd() -> None:
            cmd = cmd_entry.get().strip().lower()
            chat = self.active_chat
            if cmd in {"export json", "export html"}:
                fmt = "json" if "json" in cmd else "html"
                if self.async_call:
                    self.async_call("export", (chat, fmt))
            elif cmd == "copy node":
                pyperclip.copy(self.cfg.node_id)
                self._toast("Node ID copied")
            elif cmd == "clear chat":
                tab = self.tabs.get(chat)
                if tab:
                    tab.clear_messages()
            palette.destroy()

        ctk.CTkButton(palette, text="Run", command=run_cmd).pack(pady=8)

        help_text = (
            "export json: export current chat\n"
            "export html: export current chat\n"
            "copy node: copy local node id\n"
            "clear chat: clear only visible UI list"
        )
        ctk.CTkLabel(palette, text=help_text, justify="left").pack(padx=12, pady=10, anchor="w")

    def open_settings(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("460x470")
        win.grab_set()

        ctk.CTkLabel(win, text="Mesh TTL").pack(anchor="w", padx=12, pady=(12, 2))
        ttl_entry = ctk.CTkEntry(win)
        ttl_entry.insert(0, str(self.cfg.ttl_default))
        ttl_entry.pack(fill="x", padx=12)

        ctk.CTkLabel(win, text="Scan Interval (sec)").pack(anchor="w", padx=12, pady=(12, 2))
        scan_entry = ctk.CTkEntry(win)
        scan_entry.insert(0, str(self.cfg.scan_interval_sec))
        scan_entry.pack(fill="x", padx=12)

        ctk.CTkLabel(win, text="Max Connections").pack(anchor="w", padx=12, pady=(12, 2))
        max_conn_entry = ctk.CTkEntry(win)
        max_conn_entry.insert(0, str(self.cfg.max_connections))
        max_conn_entry.pack(fill="x", padx=12)

        ctk.CTkLabel(win, text="Group Key Passphrase").pack(anchor="w", padx=12, pady=(12, 2))
        group_key_entry = ctk.CTkEntry(win, show="*")
        group_key_entry.insert(0, self.cfg.group_passphrase)
        group_key_entry.pack(fill="x", padx=12)

        ctk.CTkLabel(win, text="Theme").pack(anchor="w", padx=12, pady=(12, 2))
        theme_opt = ctk.CTkOptionMenu(win, values=["system", "light", "dark"])
        theme_opt.set(self.cfg.theme_mode)
        theme_opt.pack(fill="x", padx=12)

        def save() -> None:
            self.cfg.ttl_default = int(ttl_entry.get())
            self.cfg.scan_interval_sec = float(scan_entry.get())
            self.cfg.max_connections = int(max_conn_entry.get())
            self.cfg.group_passphrase = group_key_entry.get().strip() or self.cfg.group_passphrase
            self.cfg.theme_mode = theme_opt.get()
            self.cfg.save()
            if self.async_call:
                self.async_call("reload_config", ())
            win.destroy()
            self._toast("Settings saved")

        ctk.CTkButton(win, text="Save", command=save).pack(pady=(18, 8))

        def clear_history() -> None:
            if self.async_call:
                self.async_call("clear_history", ())
            self._toast("History clear requested")

        ctk.CTkButton(win, text="Clear History", fg_color="#d32f2f", hover_color="#b71c1c", command=clear_history).pack(pady=6)

        ctk.CTkLabel(
            win,
            justify="left",
            text=(
                "Permissions hints:\n"
                "Windows: enable Bluetooth + location, run terminal as normal user.\n"
                "macOS: grant Bluetooth access in System Settings > Privacy.\n"
                "Linux: install BlueZ, run with Bluetooth enabled and proper udev/dbus permissions."
            ),
        ).pack(fill="x", padx=12, pady=(14, 10))
