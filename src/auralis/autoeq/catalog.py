"""Local headphone preset catalog (AutoEQ ParametricEQ files)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .parser import ParsedPreset, parse_parametric_eq_file


@dataclass(frozen=True)
class PresetInfo:
    name: str
    source: str
    form: str
    path: Path

    @property
    def label(self) -> str:
        return f"{self.name}  ·  {self.source} / {self.form}"


class PresetCatalog:
    def __init__(self, presets_dir: Path):
        self.presets_dir = Path(presets_dir)
        self._items: list[PresetInfo] = []
        self.reload()

    def reload(self) -> None:
        self._items.clear()
        index_path = self.presets_dir / "index.json"
        if index_path.exists():
            data = json.loads(index_path.read_text(encoding="utf-8-sig"))
            for row in data:
                path = self.presets_dir / row["file"]
                if path.exists():
                    self._items.append(
                        PresetInfo(
                            name=row["name"],
                            source=row.get("source", "local"),
                            form=row.get("form", "unknown"),
                            path=path,
                        )
                    )
        else:
            for path in sorted(self.presets_dir.glob("*.txt")):
                self._items.append(
                    PresetInfo(name=path.stem, source="local", form="unknown", path=path)
                )

    @property
    def items(self) -> list[PresetInfo]:
        return list(self._items)

    def search(self, query: str) -> list[PresetInfo]:
        q = query.strip().lower()
        if not q:
            return self.items
        return [p for p in self._items if q in p.name.lower() or q in p.source.lower()]

    def load(self, info: PresetInfo) -> ParsedPreset:
        return parse_parametric_eq_file(str(info.path), name=info.name)
