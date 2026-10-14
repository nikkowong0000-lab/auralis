"""Generate README frequency-response plot (no GUI required)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from auralis.autoeq.catalog import PresetCatalog  # noqa: E402
from auralis.dsp.curve import combine_response, suggested_preamp  # noqa: E402
from auralis.paths import presets_dir  # noqa: E402
from auralis.ui.theme import COLORS  # noqa: E402


def main() -> None:
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)

    catalog = PresetCatalog(presets_dir())
    info = next((p for p in catalog.items if "HD 600" in p.name), catalog.items[0])
    preset = catalog.load(info)
    freqs, gains = combine_response(preset.filters, [0] * 10, bass_boost_db=1.5)
    pre = suggested_preamp(gains)
    gains = gains + pre

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=140, facecolor=COLORS["plot_bg"])
    ax.set_facecolor(COLORS["plot_bg"])
    ax.axhline(0, color=COLORS["zero"], linewidth=1)
    ax.fill_between(freqs, gains, 0, color=COLORS["accent"], alpha=0.2)
    ax.semilogx(freqs, gains, color=COLORS["curve"], linewidth=2.4)
    ax.set_xlim(20, 20000)
    ax.set_ylim(-18, 12)
    ax.set_xlabel("Frequency (Hz)", color=COLORS["muted"])
    ax.set_ylabel("Gain (dB)", color=COLORS["muted"])
    ax.tick_params(colors=COLORS["muted"])
    ax.grid(True, which="both", color=COLORS["plot_grid"], alpha=0.75)
    for spine in ax.spines.values():
        spine.set_color(COLORS["border"])
    ax.set_title(
        f"Auralis — {info.name} (AutoEQ + light bass boost)",
        color=COLORS["text"],
        loc="left",
        fontsize=12,
    )
    fig.tight_layout()
    out = assets / "response-curve.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
