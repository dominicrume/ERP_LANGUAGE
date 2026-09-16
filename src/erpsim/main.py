"""ERP Decision Lab API — generate, decide, recall, author."""
from typing import Optional

from pathlib import Path
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, create_engine

from erpsim import generator, locales, memory, scoring, templates

engine = create_engine("sqlite:///erpsim.db", connect_args={"check_same_thread": False})
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
    try:
        scenario = generator.generate(template_id, locale, seed)
    except (templates.UnknownTemplateError, locales.UnknownLocaleError) as e:
        raise HTTPException(404, str(e))
    valid_ids = {d["id"] for d in scenario["decisions"]}
    if decision_id not in valid_ids:
        raise HTTPException(422, f"decision_id must be one of {sorted(valid_ids)}")
    result = scoring.score_decision(scenario, decision_id, choice)
    if learner_id:
        with Session(engine) as s:
            memory.record_attempt(s, learner_id, template_id, locale, result["running_score"])
    return result


@app.get("/learners/{learner_id}/progress/{template_id}")
def progress(learner_id: str, template_id: str):
    with Session(engine) as s:
        p = memory.recall(s, learner_id, template_id)
        if not p:
            return {"learner_id": learner_id, "template_id": template_id, "attempts": 0,
                    "best_score": None, "note": "no attempts yet"}
        return p.model_dump()


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
