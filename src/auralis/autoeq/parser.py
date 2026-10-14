"""Parse AutoEQ / Equalizer APO ParametricEQ text files."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from auralis.dsp.biquad import FilterType, ParametricFilter

_PREAMP_RE = re.compile(r"Preamp:\s*([+-]?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)
_FILTER_RE = re.compile(
    r"Filter\s+\d+\s*:\s*(ON|OFF)\s+(PK|LSC|HSC|LS|HS)\s+"
    r"Fc\s+(\d+(?:\.\d+)?)\s*Hz\s+"
    r"Gain\s+([+-]?\d+(?:\.\d+)?)\s*dB\s+"
    r"Q\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_TYPE_MAP = {
    "PK": FilterType.PEAKING,
    "LSC": FilterType.LOW_SHELF,
    "LS": FilterType.LOW_SHELF,
    "HSC": FilterType.HIGH_SHELF,
    "HS": FilterType.HIGH_SHELF,
}


@dataclass
class ParsedPreset:
    name: str
    preamp_db: float = 0.0
    filters: list[ParametricFilter] = field(default_factory=list)
    source_path: str | None = None


def parse_parametric_eq_text(text: str, name: str = "Custom") -> ParsedPreset:
    preamp = 0.0
    m = _PREAMP_RE.search(text)
    if m:
        preamp = float(m.group(1))

    filters: list[ParametricFilter] = []
    for match in _FILTER_RE.finditer(text):
        enabled = match.group(1).upper() == "ON"
        ftype = _TYPE_MAP[match.group(2).upper()]
        filters.append(
            ParametricFilter(
                type=ftype,
                freq_hz=float(match.group(3)),
                gain_db=float(match.group(4)),
                q=float(match.group(5)),
                enabled=enabled,
            )
        )

    if not filters:
        raise ValueError("No parametric filters found in preset text")

    return ParsedPreset(name=name, preamp_db=preamp, filters=filters)


def parse_parametric_eq_file(path: str, name: str | None = None) -> ParsedPreset:
    from pathlib import Path

    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    preset = parse_parametric_eq_text(text, name=name or p.stem)
    preset.source_path = str(p)
    return preset
