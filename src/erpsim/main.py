"""ERP Decision Lab API: generate, play a run, decide, recall, author."""
import os
from typing import Optional

from pathlib import Path
from fastapi import Body, FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, create_engine

from erpsim import authoring, generator, locales, memory, runs, scoring, templates

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

app = FastAPI(title="ERP Decision Lab", version="0.4.0")

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


# ---------------------------------------------------------------- runs
def _scenario_or_404(template_id: str, locale: str, seed: int) -> dict:
    try:
        return generator.generate(template_id, locale, seed)
    except (templates.UnknownTemplateError, locales.UnknownLocaleError) as e:
        raise HTTPException(404, str(e))
    except templates.InvalidTemplateError as e:
        raise HTTPException(422, str(e))


def _run_or_404(session: Session, run_id: str) -> runs.ScenarioRun:
    try:
        return runs.get(session, run_id)
    except runs.UnknownRunError as e:
        raise HTTPException(404, str(e))


@app.post("/runs")
def start_run(template_id: str = Form(...), locale: str = Form(...), seed: int = Form(1),
              learner_id: Optional[str] = Form(None)):
    """Start one sitting of one scenario. The run is what a score belongs to."""
    learner_id = clean_learner_id(learner_id)
    scenario = _scenario_or_404(template_id, locale, seed)
    with Session(engine) as s:
        run = runs.start(s, template_id, locale, seed, learner_id)
        return {"run": runs.state(s, run, scenario), "scenario": scenario}


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    """Everything about a run, so a learner can reload and carry on."""
    with Session(engine) as s:
        run = _run_or_404(s, run_id)
        scenario = _scenario_or_404(run.template_id, run.locale, run.seed)
        return {"run": runs.state(s, run, scenario), "scenario": scenario}


@app.post("/runs/{run_id}/decisions")
def decide_in_run(run_id: str, decision_id: str = Form(...), choice: str = Form(...),
                  learner_id: Optional[str] = Form(None)):
    """Answer one decision. The reply carries the cumulative score, which is
    the only score a learner should ever be shown (CONTEXT.md gap A)."""
    learner_id = clean_learner_id(learner_id)
    with Session(engine) as s:
        run = _run_or_404(s, run_id)
        try:
            runs.check_owner(run, learner_id)
        except runs.RunOwnershipError as e:
            raise HTTPException(403, str(e))
        scenario = _scenario_or_404(run.template_id, run.locale, run.seed)
        try:
            return runs.record_decision(s, run, scenario, decision_id, choice)
        except runs.RunConflictError as e:
            raise HTTPException(409, str(e))
        except (runs.RunIncompleteError, scoring.ScoringError) as e:
            raise HTTPException(422, str(e))


@app.post("/runs/{run_id}/complete")
def complete_run(run_id: str, learner_id: Optional[str] = Form(None)):
    """Finish the sitting and hand back the whole story: final score, every
    decision, and the one that cost the most."""
    learner_id = clean_learner_id(learner_id)
    with Session(engine) as s:
        run = _run_or_404(s, run_id)
        try:
            runs.check_owner(run, learner_id)
        except runs.RunOwnershipError as e:
            raise HTTPException(403, str(e))
        scenario = _scenario_or_404(run.template_id, run.locale, run.seed)
        try:
            return runs.complete(s, run, scenario)
        except runs.RunConflictError as e:
            raise HTTPException(409, str(e))
        except runs.RunIncompleteError as e:
            raise HTTPException(422, str(e))


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
    """Rule 7: authoring validation, fails loud before publish. Kept for the
    YAML path (an instructor who already has a file); the builder posts a
    draft to /instructor/drafts/preview instead."""
    import yaml
    try:
        data = yaml.safe_load(raw_yaml)
        templates.validate(data)
    except templates.InvalidTemplateError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, f"not valid YAML: {e}")
    return {"valid": True, "template_id": data.get("id")}


# ---------------------------------------------------------------- authoring
@app.get("/instructor/templates")
def instructor_templates():
    """The catalog an instructor manages: what exists, and what it costs to
    run it everywhere (PRODUCT.md #6 — the N x M number, shown working)."""
    rows = authoring.listing()
    locs = locales.available()
    return {"templates": rows, "locales": locs, "scenarios": len(rows) * len(locs),
            "scale_options": authoring.SCALES_WITH, "tokens": sorted(authoring.TOKENS)}


@app.get("/instructor/drafts/{template_id}")
def open_draft(template_id: str):
    """Open a published template back in the builder."""
    try:
        return authoring.to_draft(templates.load(template_id))
    except templates.UnknownTemplateError as e:
        raise HTTPException(404, str(e))


@app.post("/instructor/drafts/preview")
def preview_draft(draft: dict = Body(...), seed: int = 1):
    """The instructor's own scenario, rendered in every country before it is
    published. Invalid drafts come back as one plain sentence, never a
    stack trace and never YAML."""
    try:
        tpl = authoring.from_draft(draft)
    except authoring.DraftError as e:
        raise HTTPException(422, str(e))
    return {"valid": True, "template_id": tpl["id"], "yaml": authoring.to_yaml(tpl),
            "exists": tpl["id"] in templates.available(),
            "preview": authoring.preview(tpl, seed)}


@app.post("/instructor/drafts/publish")
def publish_draft(draft: dict = Body(...), overwrite: bool = False):
    """Publishing writes config/templates/{id}.yaml — adding an industry is
    still adding a config file (ENGINEERING.md #2), just not by hand."""
    try:
        tpl = authoring.from_draft(draft)
    except authoring.DraftError as e:
        raise HTTPException(422, str(e))
    try:
        return authoring.publish(tpl, overwrite=overwrite)
    except FileExistsError:
        raise HTTPException(409, f"A scenario with the short id '{tpl['id']}' already exists. "
                                 f"Publish again with overwrite to replace it (the old version is archived).")
    except templates.UnloadableTemplateError as e:  # pragma: no cover - defensive
        raise HTTPException(500, f"published file did not load back: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "templates": len(templates.available()), "locales": len(locales.available())}
