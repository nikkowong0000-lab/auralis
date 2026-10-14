"""Auralis main window — headphone search, AutoEQ, graphic EQ, APO export."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Sequence

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

from auralis.apo.export import build_apo_config, export_equalizer_apo
from auralis.autoeq.catalog import PresetCatalog, PresetInfo
from auralis.autoeq.parser import ParsedPreset, parse_parametric_eq_file
from auralis.dsp.biquad import ParametricFilter
from auralis.dsp.curve import (
    GRAPHIC_BANDS_HZ,
    combine_response,
    suggested_preamp,
)
from auralis.paths import exports_dir, presets_dir, user_profiles_dir
from auralis.ui.help_dialog import HelpDialog
from auralis.ui.theme import COLORS


BAND_LABELS = ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]


class AuralisApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Auralis — Headphone EQ Studio")
        self.geometry("1180x740")
        self.minsize(1020, 660)
        self.configure(fg_color=COLORS["bg"])

        self.catalog = PresetCatalog(presets_dir())
        self.current_preset: ParsedPreset | None = None
        self.current_info: PresetInfo | None = None
        self.graphic_vars: list[ctk.DoubleVar] = [ctk.DoubleVar(value=0.0) for _ in GRAPHIC_BANDS_HZ]
        self.bass_var = ctk.DoubleVar(value=0.0)
        self.preamp_var = ctk.DoubleVar(value=0.0)
        self.auto_preamp = ctk.BooleanVar(value=True)
        self._spectrum_phase = 0.0
        self._last_curve: tuple[np.ndarray, np.ndarray] | None = None

        self._build_layout()
        self._refresh_list()
        if self.catalog.items:
            self.preset_list.selection_set(0)
            self._on_select_preset()
        else:
            self._set_status("No presets found — use Import AutoEQ…", error=True)
        self.after(80, self._tick_spectrum)
        self.after(400, self._maybe_show_welcome)
        self.bind("<F1>", lambda _e: self._show_help())

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=0, width=300)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)

        brand = ctk.CTkLabel(
            left,
            text="AURALIS",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=26),
            text_color=COLORS["accent"],
        )
        brand.pack(anchor="w", padx=20, pady=(22, 0))
        ctk.CTkLabel(
            left,
            text="Headphone AutoEQ Studio",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["muted"],
        ).pack(anchor="w", padx=20, pady=(0, 6))
        self.count_label = ctk.CTkLabel(
            left,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
        )
        self.count_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.search = ctk.CTkEntry(
            left,
            placeholder_text="Search headphones…",
            fg_color=COLORS["panel_alt"],
            border_color=COLORS["border"],
        )
        self.search.pack(fill="x", padx=16, pady=(0, 8))
        self.search.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.preset_list = tk.Listbox(
            left,
            activestyle="dotbox",
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            selectbackground=COLORS["accent_dim"],
            selectforeground=COLORS["text"],
            highlightthickness=0,
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        self.preset_list.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.preset_list.bind("<<ListboxSelect>>", lambda _e: self._on_select_preset())

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(
            btn_row,
            text="Import AutoEQ…",
            fg_color=COLORS["panel_alt"],
            hover_color=COLORS["border"],
            command=self._import_preset,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            btn_row,
            text="Reset EQ",
            fg_color=COLORS["panel_alt"],
            hover_color=COLORS["border"],
            command=self._reset_manual_eq,
        ).pack(side="left", expand=True, fill="x")

        ctk.CTkButton(
            left,
            text="Help (F1)",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["panel_alt"],
            command=self._show_help,
            height=32,
        ).pack(fill="x", padx=16, pady=(0, 16))

        right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 6))
        self.title_label = ctk.CTkLabel(
            header,
            text="Select a headphone",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=22),
            text_color=COLORS["text"],
        )
        self.title_label.pack(side="left")
        self.meta_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["muted"],
        )
        self.meta_label.pack(side="left", padx=14)
        self.peak_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["warn"],
        )
        self.peak_label.pack(side="right")

        plot_frame = ctk.CTkFrame(right, fg_color=COLORS["panel"], corner_radius=12)
        plot_frame.grid(row=1, column=0, sticky="nsew", padx=22, pady=8)
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(0, weight=3)
        plot_frame.grid_rowconfigure(1, weight=1)

        self.fig = Figure(figsize=(7.5, 3.2), dpi=100, facecolor=COLORS["plot_bg"])
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.spec_fig = Figure(figsize=(7.5, 1.1), dpi=100, facecolor=COLORS["plot_bg"])
        self.spec_ax = self.spec_fig.add_subplot(111)
        self.spec_canvas = FigureCanvasTkAgg(self.spec_fig, master=plot_frame)
        self.spec_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        controls = ctk.CTkFrame(right, fg_color=COLORS["panel"], corner_radius=12)
        controls.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 10))
        controls.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            controls,
            text="Graphic EQ overlay",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        bands = ctk.CTkFrame(controls, fg_color="transparent")
        bands.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        for i, (label, var) in enumerate(zip(BAND_LABELS, self.graphic_vars)):
            col = ctk.CTkFrame(bands, fg_color="transparent")
            col.pack(side="left", expand=True, fill="both", padx=2)
            slider = ctk.CTkSlider(
                col,
                from_=-12,
                to=12,
                variable=var,
                orientation="vertical",
                height=120,
                progress_color=COLORS["accent"],
                button_color=COLORS["accent"],
                command=lambda _v: self._on_eq_change(),
            )
            slider.pack(pady=(0, 4))
            ctk.CTkLabel(col, text=label, text_color=COLORS["muted"], font=ctk.CTkFont(size=11)).pack()

        extras = ctk.CTkFrame(controls, fg_color="transparent")
        extras.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        extras.grid_columnconfigure(1, weight=1)
        extras.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(extras, text="Bass boost", text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w")
        ctk.CTkSlider(
            extras,
            from_=0,
            to=9,
            variable=self.bass_var,
            progress_color=COLORS["warn"],
            button_color=COLORS["warn"],
            command=lambda _v: self._on_eq_change(),
        ).grid(row=0, column=1, sticky="ew", padx=10)
        self.bass_value = ctk.CTkLabel(extras, text="0.0 dB", text_color=COLORS["text"], width=60)
        self.bass_value.grid(row=0, column=2, sticky="w")

        ctk.CTkLabel(extras, text="Preamp", text_color=COLORS["muted"]).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ctk.CTkSlider(
            extras,
            from_=-18,
            to=0,
            variable=self.preamp_var,
            progress_color=COLORS["accent"],
            button_color=COLORS["accent"],
            command=lambda _v: self._on_eq_change(manual_preamp=True),
        ).grid(row=1, column=1, sticky="ew", padx=10, pady=(8, 0))
        self.preamp_value = ctk.CTkLabel(extras, text="0.0 dB", text_color=COLORS["text"], width=60)
        self.preamp_value.grid(row=1, column=2, sticky="w", pady=(8, 0))
        ctk.CTkCheckBox(
            extras,
            text="Auto preamp (anti-clip)",
            variable=self.auto_preamp,
            command=self._on_eq_change,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
        ).grid(row=1, column=3, sticky="e", padx=(12, 0), pady=(8, 0))

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        ctk.CTkButton(
            actions,
            text="Export Equalizer APO",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            text_color="#041210",
            font=ctk.CTkFont(weight="bold"),
            command=self._export_apo,
            height=40,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Copy APO",
            fg_color=COLORS["panel_alt"],
            hover_color=COLORS["border"],
            command=self._copy_apo,
            height=40,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Save profile",
            fg_color=COLORS["panel_alt"],
            hover_color=COLORS["border"],
            command=self._save_profile,
            height=40,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            actions,
            text="Load profile",
            fg_color=COLORS["panel_alt"],
            hover_color=COLORS["border"],
            command=self._load_profile,
            height=40,
        ).pack(side="left")
        self.status = ctk.CTkLabel(actions, text="Ready", text_color=COLORS["muted"])
        self.status.pack(side="right")

    # ------------------------------------------------------------- helpers
    def _set_status(self, text: str, *, error: bool = False) -> None:
        self.status.configure(text=text, text_color=COLORS["danger"] if error else COLORS["muted"])

    def _show_help(self) -> None:
        HelpDialog(self, title="Auralis Help")

    def _maybe_show_welcome(self) -> None:
        marker = user_profiles_dir() / ".welcome_shown"
        if marker.exists():
            return
        HelpDialog(self, title="Welcome to Auralis")
        try:
            marker.write_text("1", encoding="utf-8")
        except OSError:
            pass

    def _apo_text(self) -> str:
        name = self.current_info.name if self.current_info else "Custom"
        return build_apo_config(
            title=name,
            autoeq_filters=self._filters(),
            graphic_gains_db=self._graphic_gains(),
            bass_boost_db=float(self.bass_var.get()),
            preamp_db=float(self.preamp_var.get()),
        )

    # ------------------------------------------------------------- catalog
    def _filtered(self) -> list[PresetInfo]:
        return self.catalog.search(self.search.get())

    def _refresh_list(self) -> None:
        items = self._filtered()
        self.preset_list.delete(0, tk.END)
        if not items:
            self.preset_list.insert(tk.END, "(no matches — clear search or Import)")
            self.count_label.configure(text=f"0 / {len(self.catalog.items)} shown")
            return
        for item in items:
            form_tag = "IE" if item.form == "in-ear" else "OE"
            self.preset_list.insert(tk.END, f"[{form_tag}]  {item.name}")
        self.count_label.configure(text=f"{len(items)} / {len(self.catalog.items)} headphones")

    def _on_select_preset(self) -> None:
        sel = self.preset_list.curselection()
        if not sel:
            return
        items = self._filtered()
        if not items:
            return
        info = items[sel[0]]
        try:
            preset = self.catalog.load(info)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Preset error", f"Could not load preset:\n{exc}")
            self._set_status(f"Failed to load {info.name}", error=True)
            return
        self.current_info = info
        self.current_preset = preset
        self.title_label.configure(text=info.name)
        self.meta_label.configure(
            text=f"{info.source} · {info.form} · {len(self.current_preset.filters)} filters"
        )
        self._on_eq_change()
        self._set_status(f"Loaded {info.name}")

    def _import_preset(self) -> None:
        path = filedialog.askopenfilename(
            title="Import AutoEQ ParametricEQ.txt",
            filetypes=[("Text / EQ", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            preset = parse_parametric_eq_file(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Import failed",
                "Could not parse file. Use an AutoEQ ParametricEQ.txt export.\n\n"
                f"Details: {exc}",
            )
            self._set_status("Import failed", error=True)
            return
        dest = presets_dir() / f"{preset.name}.txt"
        dest.write_text(Path(path).read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        index_path = presets_dir() / "index.json"
        rows: list[dict] = []
        if index_path.exists():
            rows = json.loads(index_path.read_text(encoding="utf-8-sig"))
        rows = [r for r in rows if r.get("name") != preset.name]
        rows.append(
            {"name": preset.name, "source": "imported", "form": "custom", "file": dest.name}
        )
        index_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        self.catalog.reload()
        self.search.delete(0, tk.END)
        self._refresh_list()
        names = [p.name for p in self._filtered()]
        if preset.name in names:
            idx = names.index(preset.name)
            self.preset_list.selection_clear(0, tk.END)
            self.preset_list.selection_set(idx)
            self.preset_list.see(idx)
            self._on_select_preset()
        self._set_status(f"Imported {preset.name}")
        messagebox.showinfo("Imported", f"Added preset:\n{preset.name}")

    # ----------------------------------------------------------------- EQ
    def _graphic_gains(self) -> list[float]:
        return [float(v.get()) for v in self.graphic_vars]

    def _filters(self) -> list[ParametricFilter]:
        if self.current_preset is None:
            return []
        return list(self.current_preset.filters)

    def _on_eq_change(self, manual_preamp: bool = False) -> None:
        freqs, gains_no_pre = combine_response(
            self._filters(),
            self._graphic_gains(),
            bass_boost_db=float(self.bass_var.get()),
            preamp_db=0.0,
        )
        if self.auto_preamp.get() and not manual_preamp:
            pre = suggested_preamp(gains_no_pre)
            self.preamp_var.set(round(pre, 1))
        preamp = float(self.preamp_var.get())
        gains = gains_no_pre + preamp

        self.bass_value.configure(text=f"{float(self.bass_var.get()):.1f} dB")
        self.preamp_value.configure(text=f"{preamp:.1f} dB")
        peak = float(np.max(gains_no_pre)) if len(gains_no_pre) else 0.0
        self.peak_label.configure(text=f"peak boost {peak:+.1f} dB  ·  preamp {preamp:.1f} dB")
        self._draw_curve(freqs, gains)
        self._last_curve = (freqs, gains)

    def _reset_manual_eq(self) -> None:
        for v in self.graphic_vars:
            v.set(0.0)
        self.bass_var.set(0.0)
        self._on_eq_change()
        self._set_status("Graphic EQ & bass boost reset")

    def _draw_curve(self, freqs: np.ndarray, gains: np.ndarray) -> None:
        self.ax.clear()
        self.ax.set_facecolor(COLORS["plot_bg"])
        self.ax.axhline(0, color=COLORS["zero"], linewidth=1, alpha=0.8)
        self.ax.fill_between(freqs, gains, 0, color=COLORS["accent"], alpha=0.18)
        self.ax.semilogx(freqs, gains, color=COLORS["curve"], linewidth=2.2)
        self.ax.set_xlim(20, 20000)
        self.ax.set_ylim(-18, 18)
        self.ax.set_xlabel("Frequency (Hz)", color=COLORS["muted"], fontsize=9)
        self.ax.set_ylabel("Gain (dB)", color=COLORS["muted"], fontsize=9)
        self.ax.tick_params(colors=COLORS["muted"], labelsize=8)
        self.ax.grid(True, which="both", color=COLORS["plot_grid"], alpha=0.7)
        for spine in self.ax.spines.values():
            spine.set_color(COLORS["border"])
        self.ax.set_title("Combined frequency response", color=COLORS["text"], fontsize=11, loc="left")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _tick_spectrum(self) -> None:
        """Animated spectrum preview shaped by the current EQ curve (demo visualizer)."""
        self._spectrum_phase += 0.18
        bands = 32
        xs = np.arange(bands)
        base = 0.25 + 0.55 * (0.5 + 0.5 * np.sin(xs * 0.35 + self._spectrum_phase))
        base += 0.15 * np.random.rand(bands)
        if self._last_curve is not None:
            freqs, gains = self._last_curve
            sample_f = np.logspace(np.log10(40), np.log10(16000), bands)
            eq = np.interp(sample_f, freqs, gains)
            scale = 10 ** (eq / 40.0)
            heights = np.clip(base * scale, 0.02, 1.4)
        else:
            heights = base

        self.spec_ax.clear()
        self.spec_ax.set_facecolor(COLORS["plot_bg"])
        self.spec_ax.bar(xs, heights, color=COLORS["accent"], alpha=0.85, width=0.85)
        self.spec_ax.set_ylim(0, 1.5)
        self.spec_ax.axis("off")
        self.spec_ax.set_title(
            "Spectrum preview (EQ-shaped)",
            color=COLORS["muted"],
            fontsize=9,
            loc="left",
        )
        self.spec_fig.tight_layout()
        self.spec_canvas.draw_idle()
        self.after(90, self._tick_spectrum)

    # -------------------------------------------------------------- export
    def _copy_apo(self) -> None:
        if self.current_preset is None:
            messagebox.showwarning("Nothing to copy", "Select a headphone preset first.")
            return
        text = self._apo_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Equalizer APO config copied to clipboard")

    def _export_apo(self) -> None:
        if self.current_preset is None:
            messagebox.showwarning("Nothing to export", "Select a headphone preset first.")
            return
        name = self.current_info.name if self.current_info else "Custom"
        text = self._apo_text()
        default = exports_dir() / f"auralis_{name.replace(' ', '_')}.txt"
        path = filedialog.asksaveasfilename(
            title="Export Equalizer APO config",
            defaultextension=".txt",
            initialfile=default.name,
            initialdir=str(exports_dir()),
            filetypes=[("Text", "*.txt")],
        )
        if not path:
            return
        try:
            export_equalizer_apo(path, text)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            self._set_status("Export failed", error=True)
            return
        self._set_status(f"Exported → {path}")
        messagebox.showinfo(
            "Exported",
            "Config saved.\n\n"
            "System-wide use:\n"
            "1) Install Equalizer APO\n"
            "2) Include this file from config.txt\n"
            "3) Restart audio / refresh APO",
        )

    def _save_profile(self) -> None:
        name = self.current_info.name if self.current_info else "Custom"
        payload = {
            "headphone": name,
            "graphic_eq": self._graphic_gains(),
            "bass_boost_db": float(self.bass_var.get()),
            "preamp_db": float(self.preamp_var.get()),
            "auto_preamp": bool(self.auto_preamp.get()),
            "preset_file": self.current_info.path.name if self.current_info else None,
        }
        path = filedialog.asksaveasfilename(
            title="Save Auralis profile",
            defaultextension=".json",
            initialdir=str(user_profiles_dir()),
            initialfile=f"{name.replace(' ', '_')}.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            self._set_status("Save failed", error=True)
            return
        self._set_status(f"Profile saved → {path}")

    def _load_profile(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Auralis profile",
            initialdir=str(user_profiles_dir()),
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load failed", str(exc))
            self._set_status("Load failed", error=True)
            return
        preset_file = data.get("preset_file")
        if preset_file:
            for info in self.catalog.items:
                if info.path.name == preset_file or info.name == data.get("headphone"):
                    self.search.delete(0, tk.END)
                    self._refresh_list()
                    names = [p.name for p in self._filtered()]
                    if info.name in names:
                        idx = names.index(info.name)
                        self.preset_list.selection_clear(0, tk.END)
                        self.preset_list.selection_set(idx)
                        self.preset_list.see(idx)
                        self._on_select_preset()
                    break
        gains: Sequence[float] = data.get("graphic_eq", [0.0] * 10)
        for var, g in zip(self.graphic_vars, gains):
            var.set(float(g))
        self.bass_var.set(float(data.get("bass_boost_db", 0.0)))
        self.auto_preamp.set(bool(data.get("auto_preamp", True)))
        if not self.auto_preamp.get():
            self.preamp_var.set(float(data.get("preamp_db", 0.0)))
        self._on_eq_change()
        self._set_status(f"Loaded profile {Path(path).name}")
