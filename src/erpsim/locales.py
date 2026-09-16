"""Locale loader — Rule 2: locales are data, never code."""
from pathlib import Path
import yaml

_DIR = Path(__file__).resolve().parents[2] / "config" / "locales"


class UnknownLocaleError(ValueError):
    pass


def available() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.yaml"))


def load(locale: str) -> dict:
    p = _DIR / f"{locale.lower()}.yaml"
    if not p.exists():
        raise UnknownLocaleError(f"no locale file for '{locale}'. Available: {available()}")
    return yaml.safe_load(p.read_text())
