"""Equalizer APO config generation for system-wide playback EQ."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from auralis.dsp.biquad import FilterType, ParametricFilter, peaking
from auralis.dsp.curve import GRAPHIC_BANDS_HZ


def build_apo_config(
    *,
    title: str,
    autoeq_filters: Iterable[ParametricFilter],
    graphic_gains_db: Sequence[float],
    bass_boost_db: float,
    preamp_db: float,
) -> str:
    lines = [
        f"# Auralis export — {title}",
        "# Paste into Equalizer APO config.txt (or Include this file).",
        f"Preamp: {preamp_db:.1f} dB",
        "",
        "# --- AutoEQ parametric filters ---",
    ]
    idx = 1
    for filt in autoeq_filters:
        if abs(filt.gain_db) < 1e-6 and filt.enabled:
            continue
        lines.append(filt.apo_line(idx))
        idx += 1

    if abs(bass_boost_db) >= 0.05:
        lines.append("")
        lines.append("# --- Bass boost ---")
        lines.append(
            ParametricFilter(FilterType.LOW_SHELF, 105.0, bass_boost_db, 0.70).apo_line(idx)
        )
        idx += 1

    graphic_active = any(abs(g) >= 0.05 for g in graphic_gains_db)
    if graphic_active:
        lines.append("")
        lines.append("# --- Graphic EQ overlay ---")
        for fc, g in zip(GRAPHIC_BANDS_HZ, graphic_gains_db):
            if abs(g) < 0.05:
                continue
            lines.append(peaking(fc, float(g), 1.41).apo_line(idx))
            idx += 1

    lines.append("")
    return "\n".join(lines)


def export_equalizer_apo(path: str | Path, config_text: str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(config_text, encoding="utf-8")
    return out
