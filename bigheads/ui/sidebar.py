"""Sidebar with contacts and online state."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_select_chat: Callable[[str], None],
        on_open_settings: Callable[[], None],
    ) -> None:
        super().__init__(master, corner_radius=0)
        self.on_select_chat = on_select_chat

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(self, text="BigHeads", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        self.status_lbl = ctk.CTkLabel(self, text="Offline", text_color="#f05252")
        self.status_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        self.broadcast_btn = ctk.CTkButton(self, text="Broadcast", command=lambda: self.on_select_chat("broadcast"))
        self.broadcast_btn.grid(row=2, column=0, sticky="ew", padx=12, pady=8)

        self.contact_list = ctk.CTkScrollableFrame(self)
        self.contact_list.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)
        self.contact_buttons: dict[str, ctk.CTkButton] = {}

        self.settings_btn = ctk.CTkButton(self, text="Settings", command=on_open_settings)
        self.settings_btn.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 12))

    def update_online(self, online_count: int) -> None:
        if online_count > 0:
            self.status_lbl.configure(text=f"Online ({online_count})", text_color="#22c55e")
        else:
            self.status_lbl.configure(text="Offline", text_color="#f05252")

    def set_contacts(self, node_ids: list[str]) -> None:
        for btn in self.contact_buttons.values():
            btn.destroy()
        self.contact_buttons.clear()

        for i, node_id in enumerate(node_ids):
            btn = ctk.CTkButton(
                self.contact_list,
                text=node_id,
                fg_color="transparent",
                hover_color=("#d9d9de", "#2f2f36"),
                anchor="w",
                command=lambda nid=node_id: self.on_select_chat(nid),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=6, pady=3)
            self.contact_buttons[node_id] = btn
