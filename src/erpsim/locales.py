"""Locale loader — Rule 2: locales are data, never code.
One broken file must fail loud for that locale only (BREAK.md #4)."""
import logging
from pathlib import Path
import yaml

log = logging.getLogger("erpsim.locales")
_DIR = Path(__file__).resolve().parents[2] / "config" / "locales"

# The locale_rules contract: the fields every scenario carries and that a
# template's scoring rule may reference or multiply by.
LOCALE_RULE_FIELDS = ("tax_type", "tax_rate", "tax_notes",
                      "freight_expedite_multiplier", "payment_terms_days")
REQUIRED_KEYS = {"code", "currency", "tax", "freight_expedite_multiplier", "payment_terms_days"}
REQUIRED_TAX_KEYS = {"type", "standard_rate", "notes"}


class UnknownLocaleError(ValueError):
    """No such locale (or the file exists but cannot be used)."""


class UnloadableLocaleError(UnknownLocaleError):
    """The file exists but is not valid YAML or misses required keys."""


def _load_file(p: Path) -> dict:
    try:
        data = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise UnloadableLocaleError(f"locale file {p.name} is not valid YAML: {e}") from None
    if not isinstance(data, dict):
        raise UnloadableLocaleError(f"locale file {p.name} must be a mapping")
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise UnloadableLocaleError(f"locale file {p.name} missing keys: {sorted(missing)}")
    if not isinstance(data["tax"], dict) or REQUIRED_TAX_KEYS - data["tax"].keys():
        raise UnloadableLocaleError(f"locale file {p.name}: tax needs {sorted(REQUIRED_TAX_KEYS)}")
    return data


def available() -> list[str]:
    """Locales that actually load. A broken file is logged and skipped so
    the rest of the catalog keeps working."""
    out = []
    for p in sorted(_DIR.glob("*.yaml")):
        try:
            _load_file(p)
        except UnloadableLocaleError as e:
            log.warning("skipping locale %s: %s", p.name, e)
            continue
        out.append(p.stem)
    return out


def load(locale: str) -> dict:
    p = _DIR / f"{locale.lower()}.yaml"
    if not p.exists():
        raise UnknownLocaleError(f"no locale file for '{locale}'. Available: {available()}")
    return _load_file(p)


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
