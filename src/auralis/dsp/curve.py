"""Frequency-response assembly for visualization."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

from .biquad import FilterType, ParametricFilter, _biquad_gain_db

# Classic 10-band graphic EQ centers (Hz)
GRAPHIC_BANDS_HZ: tuple[float, ...] = (
    31,
    62,
    125,
    250,
    500,
    1000,
    2000,
    4000,
    8000,
    16000,
)


def log_frequencies(n: int = 256, f_min: float = 20.0, f_max: float = 20000.0) -> np.ndarray:
    return np.logspace(np.log10(f_min), np.log10(f_max), n)


def parametric_response(
    filters: Iterable[ParametricFilter],
    freqs: Sequence[float] | np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    freqs_arr = np.asarray(freqs if freqs is not None else log_frequencies(), dtype=float)
    gains = np.zeros_like(freqs_arr)
    for filt in filters:
        gains += np.array([_biquad_gain_db(float(f), filt) for f in freqs_arr])
    return freqs_arr, gains


def graphic_eq_response(
    band_gains_db: Sequence[float],
    freqs: Sequence[float] | np.ndarray | None = None,
    q: float = 1.41,
) -> tuple[np.ndarray, np.ndarray]:
    if len(band_gains_db) != len(GRAPHIC_BANDS_HZ):
        raise ValueError(f"Expected {len(GRAPHIC_BANDS_HZ)} band gains")
    filters = [
        ParametricFilter(FilterType.PEAKING, freq_hz=fc, gain_db=float(g), q=q)
        for fc, g in zip(GRAPHIC_BANDS_HZ, band_gains_db)
    ]
    return parametric_response(filters, freqs)


def bass_boost_response(
    amount_db: float,
    freqs: Sequence[float] | np.ndarray | None = None,
    shelf_hz: float = 105.0,
) -> tuple[np.ndarray, np.ndarray]:
    from .biquad import lowshelf

    return parametric_response([lowshelf(shelf_hz, amount_db)], freqs)


def combine_response(
    autoeq_filters: Iterable[ParametricFilter],
    graphic_gains_db: Sequence[float],
    bass_boost_db: float = 0.0,
    preamp_db: float = 0.0,
    freqs: Sequence[float] | np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    freqs_arr = np.asarray(freqs if freqs is not None else log_frequencies(), dtype=float)
    _, auto = parametric_response(autoeq_filters, freqs_arr)
    _, graphic = graphic_eq_response(graphic_gains_db, freqs_arr)
    _, bass = bass_boost_response(bass_boost_db, freqs_arr)
    total = auto + graphic + bass + float(preamp_db)
    return freqs_arr, total


def suggested_preamp(gains_db: np.ndarray, headroom_db: float = 0.5) -> float:
    """Negative preamp so the loudest boost does not clip."""
    peak = float(np.max(gains_db)) if len(gains_db) else 0.0
    if peak <= 0:
        return 0.0
    return -(peak + headroom_db)
