"""First-run / Help dialog."""

from __future__ import annotations

import customtkinter as ctk

from auralis.ui.theme import COLORS

HELP_TEXT = """Auralis is a Wavelet-inspired headphone EQ studio for Windows.

How to use
1. Search and select your headphones (AutoEQ / oratory1990 presets).
2. Optionally tweak the 10-band graphic EQ and bass boost.
3. Keep Auto preamp on to reduce clipping risk.
4. Export Equalizer APO config for system-wide playback EQ.

Tips
• Import any AutoEQ “* ParametricEQ.txt” with Import AutoEQ…
• Save / Load profile keeps your headphone + slider settings.
• Without Equalizer APO you can still design curves and demo the UI.

Credits
Presets from the AutoEq project (Jaakko Pasanen) using oratory1990 data.
Auralis is independent and MIT-licensed.
"""


class HelpDialog(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, *, title: str = "Welcome to Auralis") -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("520x420")
        self.configure(fg_color=COLORS["panel"])
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="AURALIS",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=22),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=22, pady=(20, 4))

        box = ctk.CTkTextbox(
            self,
            fg_color=COLORS["panel_alt"],
            text_color=COLORS["text"],
            wrap="word",
            font=ctk.CTkFont(size=13),
        )
        box.pack(fill="both", expand=True, padx=22, pady=8)
        box.insert("1.0", HELP_TEXT)
        box.configure(state="disabled")

        ctk.CTkButton(
            self,
            text="Got it",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            text_color="#041210",
            command=self.destroy,
            width=120,
        ).pack(pady=(4, 18))
