"""Biquad filter helpers used for EQ curve visualization and APO export."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class FilterType(str, Enum):
    PEAKING = "PK"
    LOW_SHELF = "LSC"
    HIGH_SHELF = "HSC"


@dataclass(frozen=True)
class ParametricFilter:
    type: FilterType
    freq_hz: float
    gain_db: float
    q: float
    enabled: bool = True

    def apo_line(self, index: int) -> str:
        state = "ON" if self.enabled else "OFF"
        return (
            f"Filter {index}: {state} {self.type.value} "
            f"Fc {self.freq_hz:.0f} Hz Gain {self.gain_db:.1f} dB Q {self.q:.2f}"
        )


def peaking(freq_hz: float, gain_db: float, q: float) -> ParametricFilter:
    return ParametricFilter(FilterType.PEAKING, freq_hz, gain_db, q)


def lowshelf(freq_hz: float, gain_db: float, q: float = 0.7) -> ParametricFilter:
    return ParametricFilter(FilterType.LOW_SHELF, freq_hz, gain_db, q)


def highshelf(freq_hz: float, gain_db: float, q: float = 0.7) -> ParametricFilter:
    return ParametricFilter(FilterType.HIGH_SHELF, freq_hz, gain_db, q)


def _biquad_gain_db(f: float, filt: ParametricFilter) -> float:
    """Analytic magnitude response of a RBJ biquad at frequency f (Hz)."""
    if not filt.enabled or abs(filt.gain_db) < 1e-6:
        return 0.0

    # Normalize against a notional sample rate for the bilinear-warped response.
    fs = 48000.0
    w0 = 2.0 * math.pi * filt.freq_hz / fs
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    A = 10.0 ** (filt.gain_db / 40.0)
    alpha = sin_w0 / (2.0 * max(filt.q, 1e-6))

    if filt.type is FilterType.PEAKING:
        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A
    elif filt.type is FilterType.LOW_SHELF:
        two_sqrt_a_alpha = 2 * math.sqrt(A) * alpha
        b0 = A * ((A + 1) - (A - 1) * cos_w0 + two_sqrt_a_alpha)
        b1 = 2 * A * ((A - 1) - (A + 1) * cos_w0)
        b2 = A * ((A + 1) - (A - 1) * cos_w0 - two_sqrt_a_alpha)
        a0 = (A + 1) + (A - 1) * cos_w0 + two_sqrt_a_alpha
        a1 = -2 * ((A - 1) + (A + 1) * cos_w0)
        a2 = (A + 1) + (A - 1) * cos_w0 - two_sqrt_a_alpha
    else:  # HIGH_SHELF
        two_sqrt_a_alpha = 2 * math.sqrt(A) * alpha
        b0 = A * ((A + 1) + (A - 1) * cos_w0 + two_sqrt_a_alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * cos_w0)
        b2 = A * ((A + 1) + (A - 1) * cos_w0 - two_sqrt_a_alpha)
        a0 = (A + 1) - (A - 1) * cos_w0 + two_sqrt_a_alpha
        a1 = 2 * ((A - 1) - (A + 1) * cos_w0)
        a2 = (A + 1) - (A - 1) * cos_w0 - two_sqrt_a_alpha

    b0, b1, b2 = b0 / a0, b1 / a0, b2 / a0
    a1, a2 = a1 / a0, a2 / a0

    w = 2.0 * math.pi * f / fs
    z1_re, z1_im = math.cos(w), -math.sin(w)
    z2_re = math.cos(2 * w)
    z2_im = -math.sin(2 * w)

    num_re = b0 + b1 * z1_re + b2 * z2_re
    num_im = b1 * z1_im + b2 * z2_im
    den_re = 1 + a1 * z1_re + a2 * z2_re
    den_im = a1 * z1_im + a2 * z2_im

    num_mag2 = num_re * num_re + num_im * num_im
    den_mag2 = den_re * den_re + den_im * den_im
    if den_mag2 <= 0:
        return 0.0
    return 10.0 * math.log10(num_mag2 / den_mag2)
