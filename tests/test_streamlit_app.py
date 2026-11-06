"""Drives the real Streamlit app headlessly: every scenario, levers, and the spec editor."""
import os

import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "demo", "streamlit_app.py")


def start(scenario=None):
    app = AppTest.from_file(APP, default_timeout=120).run()
    assert not app.exception
    if scenario:
        app.sidebar.radio[0].set_value(scenario).run()
        assert not app.exception
    return app


def page_text(app):
    return " ".join(m.value for m in app.markdown)


def metrics(app):
    return {m.label: m.value for m in app.metric}


@pytest.mark.parametrize("scenario,phrase,label", [
    ("banks", "When Core-B fails", "Peak insolvent"),
    ("firms", "money growth", "Peak raising prices"),
    ("taxpayers", "audit rate", "Lowest compliance"),
])
def test_each_scenario_renders(scenario, phrase, label):
    app = start(scenario)
    assert phrase in page_text(app)
    assert label in metrics(app)
    assert "Max error vs exact" in metrics(app)


def test_default_headline_matches_the_readme():
    assert metrics(start())["Peak insolvent"] == "45%"


def test_bailout_changes_the_story():
    app = start()
    next(m for m in app.sidebar.multiselect if m.label == "Bail out").set_value(["Core-A"]).run()
    assert not app.exception
    assert "Bailing out Core-A" in page_text(app)
    assert metrics(app)["Bailout effect"].startswith("-")


def test_gamma_zero_freezes_the_economy():
    app = start()
    app.sidebar.slider(key="gamma.banks").set_value(0.0).run()
    assert not app.exception
    assert "every term commutes" in page_text(app)
    assert metrics(app)["Peak insolvent"] == "12%"     # 1 of 8 banks, and it never moves


def test_money_growth_lever_moves_the_result():
    app = start("firms")
    low = metrics(app)["Peak raising prices"]
    app.sidebar.slider(key="firms.money").set_value(20.0).run()
    assert not app.exception
    assert metrics(app)["Peak raising prices"] != low
    assert "de-anchor" in page_text(app)


def test_changing_the_failed_bank_clears_it_from_the_bailout():
    app = start()
    next(m for m in app.sidebar.multiselect if m.label == "Bail out").set_value(["Core-A"]).run()
    app.sidebar.selectbox(key="banks.seed").set_value("Core-A").run()
    assert not app.exception
    assert "When Core-A fails" in page_text(app)


def test_default_levers_still_show_the_cached_noisy_run():
    captions = " ".join(c.value for c in start().caption)
    assert "FakeBoston" in captions


def edit_spec(app, change):
    box = app.text_area(key="spec.banks")
    box.set_value(change(box.value))
    next(b for b in app.button if b.label == "Validate and run").click().run()
    assert not app.exception
    return " ".join(e.value for e in app.error)


def test_spec_editor_lists_validator_errors():
    errors = edit_spec(start(), lambda text: text.replace("kappa:", "kapa:"))
    assert "did you mean kappa" in errors


def test_spec_editor_rejects_bad_yaml():
    assert "Not valid YAML" in edit_spec(start(), lambda text: text + "\n  : : [")


def test_spec_editor_blocks_oversized_runs():
    errors = edit_spec(start(), lambda text: text.replace("n_times: 25", "n_times: 5000"))
    assert "hosted app allows" in errors


def test_public_limits_reject_too_many_agents():
    import yaml
    from demo.server import base_spec
    source = open(APP, encoding="utf-8").read().split("\nmain()\n")[0]
    scope = {"__file__": APP, "__name__": "limits"}
    exec(compile(source, APP, "exec"), scope)
    spec = yaml.safe_load(yaml.safe_dump(base_spec("firms")))
    spec["agents"]["grid"] = [5, 4]
    assert any("20 agents" in p for p in scope["public_limit_errors"](spec))
