"""ERP Decision Lab API — generate, decide, recall, author."""
import os
from typing import Optional

from pathlib import Path
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, create_engine

from erpsim import generator, locales, memory, scoring, templates

DEFAULT_DATABASE_URL = "sqlite:///erpsim.db"
LEARNER_ID_MAX = 64


def clean_learner_id(raw: Optional[str]) -> Optional[str]:
    """A learner_id is a name, not a path: trimmed, non-empty, no slashes,
    at most LEARNER_ID_MAX chars. None stays None (anonymous attempt)."""
    if raw is None:
        return None
    lid = raw.strip()
    if not lid:
        raise HTTPException(422, "learner_id must not be blank")
    if len(lid) > LEARNER_ID_MAX:
        raise HTTPException(422, f"learner_id must be at most {LEARNER_ID_MAX} characters")
    if "/" in lid or "\\" in lid:
        raise HTTPException(422, "learner_id must not contain slashes")
    return lid


def database_url() -> str:
    """SCALING.md #1: SQLite for dev -> Postgres for real. DSN swap only,
    via ERPSIM_DATABASE_URL (ENGINEERING.md #5: nothing inline)."""
    return os.environ.get("ERPSIM_DATABASE_URL", DEFAULT_DATABASE_URL)


def engine_kwargs(url: str) -> dict:
    """SQLite needs check_same_thread=False under uvicorn; nothing else does."""
    return {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}


def make_engine(url: str):
    return create_engine(url, **engine_kwargs(url))


engine = make_engine(database_url())
SQLModel.metadata.create_all(engine)

app = FastAPI(title="ERP Decision Lab", version="0.1.0")

_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR)), name="assets")

@app.get("/")
def frontend():
    index = _STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "ERP Decision Lab API. Frontend not found — see /catalog."}



@app.get("/catalog")
def catalog():
    """What's buildable right now: N templates x M locales, zero new code."""
    return {"templates": templates.available(), "locales": locales.available(),
            "possible_scenarios": len(templates.available()) * len(locales.available())}


@app.post("/scenarios/generate")
def generate_scenario(template_id: str = Form(...), locale: str = Form(...), seed: int = Form(1)):
    try:
        return generator.generate(template_id, locale, seed)
    except (templates.UnknownTemplateError, locales.UnknownLocaleError) as e:
        raise HTTPException(404, str(e))
    except templates.InvalidTemplateError as e:
        raise HTTPException(422, str(e))


@app.post("/decisions/score")
def score(template_id: str = Form(...), locale: str = Form(...), seed: int = Form(1),
          decision_id: str = Form(...), choice: str = Form(...),
          learner_id: Optional[str] = Form(None)):
    learner_id = clean_learner_id(learner_id)
    try:
        scenario = generator.generate(template_id, locale, seed)
    except (templates.UnknownTemplateError, locales.UnknownLocaleError) as e:
        raise HTTPException(404, str(e))
    except templates.InvalidTemplateError as e:
        raise HTTPException(422, str(e))
    decision = next((d for d in scenario["decisions"] if d["id"] == decision_id), None)
    if decision is None:
        valid_ids = sorted(d["id"] for d in scenario["decisions"])
        raise HTTPException(422, f"decision_id must be one of {valid_ids}")
    if choice not in decision["options"]:
        # BREAK.md #3: reject before scoring and before any memory write.
        raise HTTPException(422, f"choice '{choice}' is not an option for "
                                 f"'{decision_id}'. Options: {decision['options']}")
    try:
        result = scoring.score_decision(scenario, decision_id, choice)
    except scoring.ScoringError as e:
        raise HTTPException(422, str(e))
    if learner_id:
        # PRODUCT.md #4: remember what tripped the learner up, in the rule's own words.
        mistake = result["justification"][0] if result["score_delta"] < 0 else None
        with Session(engine) as s:
            memory.record_attempt(s, learner_id, template_id, locale, result["running_score"], mistake)
    return result


@app.get("/learners/{learner_id}/progress/{template_id}")
def progress(learner_id: str, template_id: str, locale: Optional[str] = None):
    """With ?locale= : that learner's record for one country. Without: the
    same learner's per-locale records plus totals. Never another learner's."""
    learner_id = clean_learner_id(learner_id)
    with Session(engine) as s:
        if locale:
            p = memory.recall(s, learner_id, template_id, locale)
            if not p:
                return {"learner_id": learner_id, "template_id": template_id, "locale": locale.lower(),
                        "attempts": 0, "best_score": None, "last_mistake": None, "note": "no attempts yet"}
            return p.model_dump()
        rows = [r.model_dump() for r in memory.recall_all(s, learner_id, template_id)]
        out = {"learner_id": learner_id, "template_id": template_id,
               "attempts": sum(r["attempts"] for r in rows),
               "best_score": max((r["best_score"] for r in rows), default=None),
               "by_locale": rows}
        if not rows:
            out["note"] = "no attempts yet"
        return out


@app.post("/instructor/templates/validate")
def validate_template(raw_yaml: str = Form(...)):
    """Rule 7: authoring validation, fails loud before publish."""
    import yaml
    try:
        data = yaml.safe_load(raw_yaml)
        templates.validate(data)
    except templates.InvalidTemplateError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, f"not valid YAML: {e}")
    return {"valid": True, "template_id": data.get("id")}


@app.get("/health")
def health():
    return {"status": "ok", "templates": len(templates.available()), "locales": len(locales.available())}
