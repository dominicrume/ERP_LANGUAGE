"""Locale loader — Rule 2: locales are data, never code."""
from pathlib import Path
import yaml

_DIR = Path(__file__).resolve().parents[2] / "config" / "locales"

# The locale_rules contract: the fields every scenario carries and that a
# template's scoring rule may reference or multiply by.
LOCALE_RULE_FIELDS = ("tax_type", "tax_rate", "tax_notes",
                      "freight_expedite_multiplier", "payment_terms_days")


class UnknownLocaleError(ValueError):
    pass


def available() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.yaml"))


def load(locale: str) -> dict:
    p = _DIR / f"{locale.lower()}.yaml"
    if not p.exists():
        raise UnknownLocaleError(f"no locale file for '{locale}'. Available: {available()}")
    return yaml.safe_load(p.read_text())


def rules(loc: dict) -> dict:
    """Flatten a locale file into the locale_rules dict merged into scenarios."""
    tax = loc["tax"]
    return {
        "tax_type": tax["type"],
        "tax_rate": tax["standard_rate"],
        "tax_notes": tax["notes"],
        "freight_expedite_multiplier": loc["freight_expedite_multiplier"],
        "payment_terms_days": loc["payment_terms_days"],
    }
