"""Resolve project data paths whether run from source or frozen .exe."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: data lives next to the executable
        return Path(sys.executable).resolve().parent
    # src/auralis/paths.py -> repo root
    return Path(__file__).resolve().parents[2]


def presets_dir() -> Path:
    return project_root() / "data" / "presets"


def exports_dir() -> Path:
    d = project_root() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_profiles_dir() -> Path:
    d = project_root() / "userconfigs"
    d.mkdir(parents=True, exist_ok=True)
    return d
