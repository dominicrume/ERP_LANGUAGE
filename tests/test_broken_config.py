"""BREAK.md #4 (Firefighter): one broken locale or template file must 404
for itself only, be excluded from the catalog, and be logged by name.
The rest of the API keeps working. Broken files are written to tmp_path,
never committed."""
import logging
import shutil
from pathlib import Path

import pytest
from erpsim import locales, templates

REAL_LOCALES = Path(locales._DIR)
REAL_TEMPLATES = Path(templates._DIR)


@pytest.fixture
def broken_locale_dir(tmp_path, monkeypatch):
    d = tmp_path / "locales"
    shutil.copytree(REAL_LOCALES, d)
    (d / "zz_typo.yaml").write_text("code: ZZ\ncurrency: [unclosed\n")
    (d / "zz_thin.yaml").write_text("code: ZZ\ncurrency: ZZD\n")   # parses, but missing keys
    monkeypatch.setattr(locales, "_DIR", d)
    return d


@pytest.fixture
def broken_template_dir(tmp_path, monkeypatch):
    d = tmp_path / "templates"
    shutil.copytree(REAL_TEMPLATES, d)
    (d / "zz_typo.yaml").write_text("id: zz\ntitle: [unclosed\n")
    (d / "zz_thin.yaml").write_text("id: zz\nindustry: x\n")   # parses, fails validate
    monkeypatch.setattr(templates, "_DIR", d)
    return d


def test_broken_locale_is_excluded_from_available(broken_locale_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="erpsim.locales"):
        avail = locales.available()
    assert "zz_typo" not in avail and "zz_thin" not in avail
    assert "uk" in avail and len(avail) == 2
    assert "zz_typo.yaml" in caplog.text and "zz_thin.yaml" in caplog.text


def test_broken_locale_load_fails_loud_and_structured(broken_locale_dir):
    with pytest.raises(locales.UnloadableLocaleError, match="zz_typo.yaml is not valid YAML"):
        locales.load("zz_typo")
    with pytest.raises(locales.UnloadableLocaleError, match="missing keys"):
        locales.load("zz_thin")
    assert locales.load("uk")["currency"] == "GBP"


def test_broken_template_is_excluded_from_available(broken_template_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="erpsim.templates"):
        avail = templates.available()
    assert avail == ["heatwave_demand", "made_to_order"]
    assert "zz_typo.yaml" in caplog.text and "zz_thin.yaml" in caplog.text


def test_broken_template_load_fails_loud_and_structured(broken_template_dir):
    with pytest.raises(templates.UnloadableTemplateError, match="not valid YAML"):
        templates.load("zz_typo")
    with pytest.raises(templates.UnloadableTemplateError, match="is invalid"):
        templates.load("zz_thin")


def test_api_isolates_a_broken_locale(client, broken_locale_dir):
    cat = client.get("/catalog").json()
    assert "zz_typo" not in cat["locales"] and cat["possible_scenarios"] == 4
    r = client.post("/scenarios/generate", data=dict(template_id="heatwave_demand", locale="zz_typo", seed=1))
    assert r.status_code == 404 and "not valid YAML" in r.json()["detail"]
    r = client.post("/decisions/score", data=dict(template_id="heatwave_demand", locale="zz_typo", seed=1,
                                                   decision_id="freight_choice", choice="standard"))
    assert r.status_code == 404
    assert client.post("/scenarios/generate", data=dict(template_id="heatwave_demand", locale="uk", seed=1)).status_code == 200
    assert client.get("/health").json()["locales"] == 2


def test_api_isolates_a_broken_template(client, broken_template_dir):
    cat = client.get("/catalog").json()
    assert cat["templates"] == ["heatwave_demand", "made_to_order"]
    r = client.post("/scenarios/generate", data=dict(template_id="zz_thin", locale="uk", seed=1))
    assert r.status_code == 404 and "is invalid" in r.json()["detail"]
    assert client.post("/scenarios/generate", data=dict(template_id="made_to_order", locale="uk", seed=1)).status_code == 200
    assert client.get("/health").json()["templates"] == 2
