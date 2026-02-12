"""Message bubble widget."""

from __future__ import annotations

import customtkinter as ctk


class MessageBubble(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, text: str, meta: str, outgoing: bool) -> None:
        fg = ("#2f7ef7", "#1d4d99") if outgoing else ("#e7e7ea", "#2a2a2e")
        tc = ("white", "#f6f6f6") if outgoing else ("#222", "#ddd")
        super().__init__(master, fg_color=fg, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(
            self,
            text=text,
            text_color=tc,
            justify="left",
            anchor="w",
            wraplength=460,
            font=ctk.CTkFont(size=13),
        )
        lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))

        meta_lbl = ctk.CTkLabel(
            self,
            text=meta,
            justify="right",
            anchor="e",
            text_color=("#f1f1f3", "#b8c1d1") if outgoing else ("#555", "#999"),
            font=ctk.CTkFont(size=10),
        )
        meta_lbl.grid(row=1, column=0, sticky="e", padx=10, pady=(0, 6))
