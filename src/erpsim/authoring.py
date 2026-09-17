"""Instructor authoring (PRODUCT.md #5): a real authoring surface, not a
config file exposed as a UI.

The UI sends a DRAFT — plain-language fields, friendly [tokens] in reasons,
KPI weights as percentages. This module turns a draft into a template dict
(the same shape as config/templates/*.yaml), validates it with the one
validator, renders a preview across every locale, and publishes it as a
YAML file. The YAML file stays the canonical artefact (ENGINEERING.md #2):
publishing IS adding a config file, just not by hand.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

from . import generator, locales, runs, scoring, templates

log = logging.getLogger("erpsim.authoring")

# Friendly tokens an instructor sees  <->  format fields the interpreter uses.
TOKENS = {
    "[country]": "{locale}",
    "[currency]": "{currency}",
    "[points]": "{delta}",
    "[choice]": "{choice}",
    "[expedite multiplier]": "{freight_expedite_multiplier}",
    "[payment terms]": "{payment_terms_days}",
    "[tax rate]": "{tax_percent}",
    "[tax type]": "{tax_type}",
}
_FIELD_TO_TOKEN = {v.strip("{}"): k for k, v in TOKENS.items()}
# Legacy hand-written templates use format specs, e.g. {points:+d}; map the
# field name regardless of spec when showing them in the builder.
_FIELD_TO_TOKEN["points"] = "[points]"

# What an option's points may scale with, in instructor words.
SCALES_WITH = {
    "freight_expedite_multiplier": "the country's expedite freight multiplier",
    "payment_terms_days": "the country's payment terms (days)",
    "tax_rate": "the country's standard tax rate",
}

ARCHIVE_DIR = "_archive"


# A scenario is prose, not a payload. These caps keep an authored file
# readable and keep junk out of config/templates, where it would be served
# to every learner. They are generous for real writing and hostile to a
# script (the body-size limit in web.py is the outer bound).
LIMITS = {
    "title": 120, "industry": 60, "narrative": 2000, "product": 80, "label": 200,
    "option_label": 120, "reason": 400, "kpi_name": 60,
}
COUNTS = {"products": 24, "decisions": 12, "options": 8, "impacts": 8, "kpis": 8}


class DraftError(ValueError):
    """Instructor-facing validation failure. Message is plain language."""


def slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return s[:max_len].strip("_")


def reason_to_template(friendly: str) -> str:
    out = friendly
    for token, field in TOKENS.items():
        out = out.replace(token, field)
    return out


def reason_to_friendly(template_reason: str) -> str:
    def repl(m):
        name = m.group(1)
        return _FIELD_TO_TOKEN.get(name, m.group(0))
    return re.sub(r"\{([a-z_]+)(?::[^}]*)?\}", repl, template_reason)


# ---------------------------------------------------------------- draft -> template
def _impact_from_draft(decision_label: str, option_label: str, impacts: list, kpi_keys: dict) -> dict:
    """Turn the builder's per-KPI rows into the template's impact mapping.
    An impact on a KPI the scenario does not measure is refused here, in the
    instructor's own words, rather than at publish time."""
    out = {}
    for row in impacts:
        key = slug(row.get("kpi"))
        if key not in kpi_keys:
            raise DraftError(f"Decision '{decision_label}', option '{option_label}': "
                             f"'{row.get('kpi')}' is not one of the KPIs this scenario measures "
                             f"({', '.join(kpi_keys.values()) or 'none yet'})")
        if key in out:
            raise DraftError(f"Decision '{decision_label}', option '{option_label}': "
                             f"'{row.get('kpi')}' is listed twice")
        try:
            pts = row.get("points", 0)
            pts = int(pts) if float(pts).is_integer() else float(pts)
        except (TypeError, ValueError):
            raise DraftError(f"Decision '{decision_label}', option '{option_label}', "
                             f"KPI '{row.get('kpi')}': points must be a number")
        effect = {"points": pts}
        scales = row.get("scales_with") or None
        if scales:
            if scales not in SCALES_WITH:
                raise DraftError(f"Decision '{decision_label}', option '{option_label}': can only scale with "
                                 f"{', '.join(SCALES_WITH.values())}")
            effect["scales_with"] = scales
        out[key] = effect
    return out


def _capped(value: str, limit_key: str, what: str) -> str:
    """Length checks that read like a person wrote them, because an
    instructor sees them."""
    text = str(value).strip()
    limit = LIMITS[limit_key]
    if len(text) > limit:
        raise DraftError(f"{what} is too long: {len(text)} characters, the most is {limit}")
    return text


def _counted(items: list, count_key: str, what: str) -> list:
    limit = COUNTS[count_key]
    if len(items) > limit:
        raise DraftError(f"{what}: {len(items)} is more than the most this supports, {limit}")
    return items


def _req(d: dict, key: str, what: str) -> Any:
    v = d.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        raise DraftError(f"{what} is missing")
    return v


def from_draft(draft: dict) -> dict:
    """Convert the builder's draft into a template dict. Raises DraftError
    with a sentence an instructor can act on."""
    if not isinstance(draft, dict):
        raise DraftError("draft must be an object")
    title = _capped(_req(draft, "title", "A title"), "title", "The title")
    tid = str(draft.get("id") or slug(title)).strip()
    if not templates.ID_PATTERN.match(tid):
        raise DraftError("The short id may only use lowercase letters, digits and underscores (1-64 chars)")
    industry = _capped(_req(draft, "industry", "An industry"), "industry", "The industry")
    narrative = _capped(_req(draft, "narrative", "The story"), "narrative", "The story")
    products = [_capped(p, "product", "A product name")
                for p in _counted(list(draft.get("product_pool") or []), "products", "Products")
                if str(p).strip()]
    if not products:
        raise DraftError("Add at least one product the story can be about")
    if "{{product}}" not in narrative:
        raise DraftError("The story needs to mention the product: use 'Insert product' where it belongs")

    kpis_in = draft.get("kpi_weights") or {}
    kpi_keys = {slug(name): name for name in kpis_in if slug(name)}

    decisions_in = draft.get("decisions") or []
    if not decisions_in:
        raise DraftError("Add at least one decision")
    _counted(decisions_in, "decisions", "Decisions")
    decisions, seen = [], set()
    for i, d in enumerate(decisions_in, 1):
        label = _capped(_req(d, "label", f"Decision {i}'s question"), "label",
                        f"Decision {i}'s question")
        did = str(d.get("id") or slug(label)).strip()
        if not templates.ID_PATTERN.match(did):
            raise DraftError(f"Decision {i}: the short name may only use lowercase letters, digits and underscores")
        if did in seen:
            raise DraftError(f"Decision {i}: the short name '{did}' is already used by another decision")
        seen.add(did)
        opts_in = _counted(list(d.get("options") or []), "options", f"Decision '{label}' options")
        if len(opts_in) < 2:
            raise DraftError(f"Decision '{label}' needs at least two options")
        options, scoring_block, seen_opt = [], {}, set()
        for j, o in enumerate(opts_in, 1):
            olabel = _capped(_req(o, "label", f"Decision '{label}', option {j}'s name"),
                             "option_label", f"Decision '{label}', option {j}'s name")
            oid = str(o.get("id") or slug(olabel)).strip()
            if not oid or oid in seen_opt:
                raise DraftError(f"Decision '{label}': option names must be distinct ('{olabel}')")
            seen_opt.add(oid)
            reason = _capped(o.get("reason") or "", "reason",
                             f"Decision '{label}', option '{olabel}': the reason")
            if not reason:
                raise DraftError(f"Decision '{label}', option '{olabel}': write the reason learners will see")
            rule = {"reason": reason_to_template(reason)}
            impacts = [i for i in _counted(list(o.get("impacts") or []), "impacts",
                                          f"Decision '{label}', option '{olabel}': measures")
                       if str(i.get("kpi") or "").strip()]
            if impacts:
                rule["impact"] = _impact_from_draft(label, olabel, impacts, kpi_keys)
            elif "points" not in o:
                # A draft that carries neither is a client that has dropped the
                # scoring, not a choice that does nothing. Fail loud (Rule 4).
                raise DraftError(f"Decision '{label}', option '{olabel}': say what this choice "
                                 f"does to at least one of the KPIs this scenario measures")
            else:
                # Legacy, unweighted: a single points value on the option.
                try:
                    points = o.get("points", 0)
                    points = int(points) if float(points).is_integer() else float(points)
                except (TypeError, ValueError):
                    raise DraftError(f"Decision '{label}', option '{olabel}': points must be a number")
                rule["points"] = points
                mult = o.get("multiply_by") or None
                if mult:
                    if mult not in SCALES_WITH:
                        raise DraftError(f"Decision '{label}', option '{olabel}': can only scale with "
                                         f"{', '.join(SCALES_WITH.values())}")
                    rule["multiply_by"] = mult
            options.append(oid)
            scoring_block[oid] = rule
        decisions.append({"id": did, "label": label, "options": options, "scoring": scoring_block})

    kpis = {}
    _counted(list(kpis_in), "kpis", "Measures")
    for name, pct in kpis_in.items():
        _capped(name, "kpi_name", f"The measure name '{name}'")
        key = slug(name)
        if not key:
            continue
        try:
            kpis[key] = float(pct) / 100.0
        except (TypeError, ValueError):
            raise DraftError(f"KPI '{name}': the weight must be a number of percent")
    if not kpis:
        raise DraftError("Add at least one KPI this scenario measures")
    total = round(sum(kpis.values()) * 100)
    if total != 100:
        raise DraftError(f"KPI weights must add up to 100%, they add up to {total}%")

    tpl = {"id": tid, "industry": industry, "title": title, "narrative": narrative,
           "product_pool": products, "decisions": decisions, "kpi_weights": kpis}
    try:
        templates.validate(tpl)
    except templates.InvalidTemplateError as e:
        raise DraftError(str(e))
    return tpl


def to_draft(tpl: dict) -> dict:
    """The reverse: open an existing template in the builder."""
    decisions = []
    for d in tpl["decisions"]:
        opts = []
        for oid in d["options"]:
            rule = d["scoring"][oid]
            opt = {"id": oid, "label": oid.replace("_", " "),
                   "reason": reason_to_friendly(rule["reason"]), "impacts": []}
            if "impact" in rule:
                for kpi, effect in rule["impact"].items():
                    opt["impacts"].append({"kpi": kpi.replace("_", " "), "points": effect["points"],
                                           "scales_with": effect.get("scales_with")})
            else:
                # Published before KPI weighting: offer it as one impact on the
                # first KPI, so editing it converts rather than flattens.
                first_kpi = next(iter(tpl["kpi_weights"]), None)
                opt["legacy_points"] = rule.get("points", 0)
                if first_kpi is not None:
                    opt["impacts"].append({"kpi": first_kpi.replace("_", " "),
                                           "points": rule.get("points", 0),
                                           "scales_with": rule.get("multiply_by")})
            opts.append(opt)
        decisions.append({"id": d["id"], "label": d["label"], "options": opts})
    return {"id": tpl["id"], "title": tpl["title"], "industry": tpl["industry"],
            "narrative": tpl["narrative"].strip(), "product_pool": list(tpl["product_pool"]),
            "decisions": decisions,
            "kpi_weights": {k: round(v * 100) for k, v in tpl["kpi_weights"].items()}}


# ---------------------------------------------------------------- preview / publish
def _path(kind: str, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The best or worst way through a scenario, so an instructor sees the
    range a learner can actually finish on. Scored here, never in the
    browser (ENGINEERING.md #6)."""
    pick = max if kind == "best" else min
    chosen = [pick(d["options"], key=lambda o: o["score_delta"]) for d in decisions]
    total = runs.BASE_SCORE + sum(o["score_delta"] for o in chosen)
    return {"final_score": runs.clamp(total),
            "choices": [{"decision_id": d["id"], "choice": o["choice"], "score_delta": o["score_delta"]}
                        for d, o in zip(decisions, chosen)]}


def preview(tpl: dict, seed: int = 1) -> dict:
    """Render the instructor's scenario in EVERY country: the story, the
    locale facts, and what each option scores there. This is PRODUCT.md #6
    applied to the instructor's own work — four distinct outcomes, shown."""
    out = []
    for lid in locales.available():
        s = generator.generate_from(tpl, locales.load(lid), seed)
        decisions = []
        for d in s["decisions"]:
            decisions.append({"id": d["id"], "label": d["label"], "options": [
                {"choice": oid, **{k: v for k, v in scoring.score_decision(s, d["id"], oid).items()
                                   if k in ("score_delta", "justification", "kpi_breakdown")}}
                for oid in d["options"]]})
        out.append({"locale_id": lid, "locale": s["locale"], "currency": s["currency"],
                    "narrative": s["narrative"], "locale_rules": s["locale_rules"],
                    "decisions": decisions,
                    "best_run": _path("best", decisions), "worst_run": _path("worst", decisions)})
    return {"template_id": tpl["id"], "title": tpl["title"], "locales": out}


def to_yaml(tpl: dict) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    head = f"# Authored in the instructor builder, {stamp}. One file = one industry (ENGINEERING.md #2).\n"
    return head + yaml.safe_dump(tpl, sort_keys=False, allow_unicode=True, width=100)


def publish(tpl: dict, overwrite: bool = False) -> dict:
    """Write config/templates/{id}.yaml. Existing file: refuse unless
    overwrite, and archive the previous version first (cheap versioning)."""
    path = Path(templates._DIR) / f"{tpl['id']}.yaml"
    existed = path.exists()
    if existed and not overwrite:
        raise FileExistsError(tpl["id"])
    archived = None
    if existed:
        adir = path.parent / ARCHIVE_DIR
        adir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = adir / f"{tpl['id']}.{stamp}.yaml"
        archived.write_text(path.read_text())
    path.write_text(to_yaml(tpl))
    templates.load(tpl["id"])  # must round-trip through the real loader
    log.info("published template %s (%s)", tpl["id"], "overwrote" if existed else "new")
    return {"published": tpl["id"], "path": str(path), "overwrote": existed,
            "archived": str(archived) if archived else None,
            "locales": locales.available()}


def listing() -> list[dict]:
    out = []
    for tid in templates.available():
        t = templates.load(tid)
        out.append({"id": tid, "title": t["title"], "industry": t["industry"],
                    "decisions": len(t["decisions"]),
                    "options": sum(len(d["options"]) for d in t["decisions"]),
                    "products": len(t["product_pool"])})
    return out
