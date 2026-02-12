"""Chat tab UI for broadcast/private chats."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import emoji

from ui.components import MessageBubble


class ChatTab(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        chat_id: str,
        local_node_id: str,
        on_send_text: Callable[[str, str], None],
        on_send_file: Callable[[str, Path, bool], None],
        on_search: Callable[[str, str], None],
        on_typing: Callable[[str, bool], None],
        on_reaction: Callable[[str, str, str], None],
    ) -> None:
        super().__init__(master)
        self.chat_id = chat_id
        self.local_node_id = local_node_id
        self.on_send_text = on_send_text
        self.on_send_file = on_send_file
        self.on_search = on_search
        self.on_typing = on_typing
        self.on_reaction = on_reaction
        self.last_message_id: str | None = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        top.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(top, placeholder_text="Search in chat...")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda _: self.on_search(self.chat_id, self.search_entry.get()))

        self.messages_frame = ctk.CTkScrollableFrame(self)
        self.messages_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        self.messages_frame.grid_columnconfigure(0, weight=1)

        bottom = ctk.CTkFrame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(4, 10))
        bottom.grid_columnconfigure(1, weight=1)

        emoji_btn = ctk.CTkButton(bottom, text="😀", width=36, command=self._insert_emoji)
        emoji_btn.grid(row=0, column=0, padx=(0, 8), pady=8)

        self.input_entry = ctk.CTkEntry(bottom, placeholder_text="Write a message...")
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        self.input_entry.bind("<KeyRelease>", self._typing_changed)
        self.input_entry.bind("<Return>", lambda _: self._send_text())

        attach_btn = ctk.CTkButton(bottom, text="Attach", width=72, command=self._pick_attachment)
        attach_btn.grid(row=0, column=2, padx=(0, 8), pady=8)

        send_btn = ctk.CTkButton(bottom, text="Send", width=72, command=self._send_text)
        send_btn.grid(row=0, column=3, pady=8)

        react_btn = ctk.CTkButton(bottom, text="React", width=72, command=self._react_to_last)
        react_btn.grid(row=0, column=4, padx=(8, 0), pady=8)

    def _typing_changed(self, _: object) -> None:
        is_typing = len(self.input_entry.get().strip()) > 0
        self.on_typing(self.chat_id, is_typing)

    def _insert_emoji(self) -> None:
        picker = ctk.CTkToplevel(self)
        picker.title("Emoji")
        picker.geometry("260x180")
        sample = [":thumbs_up:", ":red_heart:", ":fire:", ":rocket:", ":grinning_face:", ":crying_face:"]
        for i, token in enumerate(sample):
            em = emoji.emojize(token)
            btn = ctk.CTkButton(
                picker,
                text=em,
                width=36,
                command=lambda e=em: (self.input_entry.insert("end", e), picker.destroy()),
            )
            btn.grid(row=i // 3, column=i % 3, padx=8, pady=8)

    def _pick_attachment(self) -> None:
        path = filedialog.askopenfilename(title="Attach file or image")
        if not path:
            return
        p = Path(path)
        as_image = p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.on_send_file(self.chat_id, p, as_image)

    def _send_text(self) -> None:
        text = self.input_entry.get().strip()
        if not text:
            return
        self.on_send_text(self.chat_id, text)
        self.input_entry.delete(0, "end")
        self.on_typing(self.chat_id, False)

    def _react_to_last(self) -> None:
        if self.last_message_id:
            self.on_reaction(self.chat_id, self.last_message_id, "heart")

    def clear_messages(self) -> None:
        for w in self.messages_frame.winfo_children():
            w.destroy()

    def add_message(self, env: dict[str, object]) -> None:
        sender = str(env.get("from", "?"))
        ts = float(env.get("timestamp", 0.0))
        payload = env.get("payload")

        if isinstance(payload, dict):
            if "text" in payload:
                body = str(payload["text"])
            elif "data" in payload and "name" in payload:
                body = f"[{env.get('type')}] {payload.get('name')} (chunk {payload.get('chunk_index', 0) + 1}/{payload.get('chunk_total', 1)})"
            else:
                body = str(payload)
        else:
            body = str(payload)

        outgoing = sender == self.local_node_id
        when = dt.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        meta = f"{sender}  {when}"

        row = len(self.messages_frame.winfo_children())
        anchor = "e" if outgoing else "w"
        wrap = ctk.CTkFrame(self.messages_frame, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        wrap.grid_columnconfigure(0, weight=1)

        bubble = MessageBubble(wrap, body, meta, outgoing)
        if outgoing:
            bubble.grid(row=0, column=0, sticky="e", padx=(120, 6))
        else:
            bubble.grid(row=0, column=0, sticky="w", padx=(6, 120))

        self.last_message_id = str(env.get("msg_id", self.last_message_id or ""))
        self.messages_frame._parent_canvas.yview_moveto(1.0)  # type: ignore[attr-defined]
