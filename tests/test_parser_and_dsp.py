from pathlib import Path

from auralis.autoeq.parser import parse_parametric_eq_text
from auralis.dsp.curve import combine_response, suggested_preamp
from auralis.apo.export import build_apo_config

SAMPLE = """
Preamp: -6.3 dB
Filter 1: ON LSC Fc 105 Hz Gain 6.5 dB Q 0.70
Filter 2: ON PK Fc 125 Hz Gain -2.7 dB Q 0.55
Filter 3: ON PK Fc 8445 Hz Gain 3.3 dB Q 1.61
"""


def test_parse_parametric_eq():
    preset = parse_parametric_eq_text(SAMPLE, name="HD 600")
    assert preset.preamp_db == -6.3
    assert len(preset.filters) == 3
    assert preset.filters[0].freq_hz == 105


def test_combine_and_preamp():
    preset = parse_parametric_eq_text(SAMPLE)
    freqs, gains = combine_response(preset.filters, [0] * 10, bass_boost_db=2.0)
    assert len(freqs) == len(gains)
    pre = suggested_preamp(gains)
    assert pre <= 0


def test_apo_export_contains_filters():
    preset = parse_parametric_eq_text(SAMPLE, name="Test")
    text = build_apo_config(
        title="Test",
        autoeq_filters=preset.filters,
        graphic_gains_db=[0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        bass_boost_db=1.5,
        preamp_db=-4.0,
    )
    assert "Preamp: -4.0 dB" in text
    assert "Filter 1:" in text
    assert "Bass boost" in text


def test_bundled_preset_file_exists():
    root = Path(__file__).resolve().parents[1]
    sample = root / "data" / "presets" / "Sennheiser HD 600.txt"
    assert sample.exists()
