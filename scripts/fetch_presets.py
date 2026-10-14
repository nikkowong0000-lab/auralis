"""Download popular AutoEQ ParametricEQ presets into data/presets/."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "presets"

# (form, model name as used in AutoEq results/oratory1990)
PRESETS: list[tuple[str, str]] = [
    ("over-ear", "Sennheiser HD 600"),
    ("over-ear", "Sennheiser HD 560S"),
    ("over-ear", "Sennheiser HD 650"),
    ("over-ear", "Sony WH-1000XM4"),
    ("over-ear", "Sony WH-1000XM5"),
    ("over-ear", "Audio-Technica ATH-M50x"),
    ("over-ear", "Audio-Technica ATH-R70x"),
    ("over-ear", "Beyerdynamic DT 770 Pro"),
    ("over-ear", "Beyerdynamic DT 990 Pro"),
    ("over-ear", "HIFIMAN Edition XS"),
    ("over-ear", "Bose QuietComfort 45"),
    ("over-ear", "AKG K371"),
    ("in-ear", "Sony WF-1000XM5"),
    ("in-ear", "Sony WF-1000XM4"),
    ("in-ear", "7Hz Salnotes Zero"),
]


def fetch(form: str, name: str) -> str | None:
    enc = quote(name)
    url = (
        "https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/"
        f"results/oratory1990/{form}/{enc}/{enc}%20ParametricEQ.txt"
    )
    try:
        with urlopen(url, timeout=30) as resp:  # noqa: S310 — trusted AutoEq URL
            text = resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError):
        return None
    if "Filter" not in text:
        return None
    return text


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, str]] = []
    for form, name in PRESETS:
        text = fetch(form, name)
        if not text:
            print(f"SKIP {name}")
            continue
        path = OUT / f"{name}.txt"
        path.write_text(text, encoding="utf-8")
        index.append(
            {"name": name, "source": "oratory1990", "form": form, "file": path.name}
        )
        print(f"OK   {name}")
    (OUT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Wrote {len(index)} presets → {OUT}")


if __name__ == "__main__":
    main()
