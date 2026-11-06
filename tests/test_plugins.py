"""Tests for Isha's workstream: specs, validator, plugins, CLI.

    python -m pytest tests -q
"""
import copy
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from plugins import REGISTRY
from plugins.banks import coupling_matrix, egj_dependency, holdings_matrix
from plugins.common import grid_edges
from qecon.api import exact_series, prepare, run_spec
from qecon.spec import SpecError, load_spec, validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = {name: os.path.join(ROOT, "specs", f"{name}.yaml") for name in REGISTRY}
FAST = ["simulation.n_times=4", "simulation.steps=4", "simulation.t_max=1.0"]


def spec(name):
    return load_spec(SPECS[name])


# ---- validator ---------------------------------------------------------------------
@pytest.mark.parametrize("name", list(REGISTRY))
def test_shipped_specs_are_valid(name):
    validate(spec(name))


def test_bad_spec_lists_every_error():
    s = spec("banks")
    s["network"]["holdings"].append([0, 99, 0.1])        # index out of range
    s["initial"]["ones"] = [1, 1]                         # duplicate
    s["simulation"]["order"] = 3                          # bad order
    with pytest.raises(SpecError) as e:
        validate(s)
    msg = str(e.value)
    assert "3 problems" in msg
    assert "out of range" in msg and "listed twice" in msg and "simulation.order" in msg


def test_column_sum_must_be_below_one():
    s = spec("banks")
    s["network"]["holdings"] = [[1, 0, 0.6], [2, 0, 0.5]]
    with pytest.raises(SpecError, match="column 0 sums to 1.100"):
        validate(s)


def test_unknown_preset():
    with pytest.raises(SpecError, match="not one of"):
        validate({"preset": "crypto"})


def test_too_many_agents():
    s = spec("firms")
    s["agents"]["grid"] = [5, 5]
    with pytest.raises(SpecError, match="GiB per statevector"):
        validate(s)


def test_gamma_zero_warns():
    _, _, warns = prepare(SPECS["banks"], ["uncertainty.gamma=0"])
    assert any("nothing will move" in w for w in warns)


def test_chain_without_field_warns():
    s = spec("firms")
    s["agents"]["grid"] = [6, 1]
    s["fields"].update(credibility=0.0, money_growth=2.0, target=2.0, disorder={"sigma": 0})
    _, warns = validate(s)
    assert any("free-fermion" in w for w in warns)


# ---- banks math --------------------------------------------------------------------
def test_egj_columns_sum_to_one():
    s = spec("banks")
    C = holdings_matrix(s["agents"]["n"], s["network"]["holdings"])
    assert np.allclose(egj_dependency(C).sum(axis=0), 1.0)


def test_bank_couplings_symmetric_and_scaled():
    pl, s, _ = prepare(SPECS["banks"])
    n, edges, h, gamma = pl.system()
    assert all(i < j for i, j in edges)
    assert max(edges.values()) == pytest.approx(s["network"]["J_scale"])
    C = holdings_matrix(n, s["network"]["holdings"])
    S = coupling_matrix(C)
    assert np.allclose(S, S.T) and np.all(np.diag(S) == 0)
    assert len(edges) == 9          # the 9 direct relationships survive min_coupling = 0.2


def test_bank_field_signs():
    base, _, _ = prepare(SPECS["banks"], ["fields.shock.nodes=[]"])
    _, _, h, _ = base.system()
    s = base.spec["fields"]
    for hi, buf in zip(h, s["capital_buffer"]):
        assert (hi > 0) == (buf > s["regulatory_min"])     # above the minimum -> solvent-favouring
    shocked, _, _ = prepare(SPECS["banks"], ["fields.shock.nodes=[1]"])
    assert shocked.system()[2][1] < 0
    bailed, _, _ = prepare(SPECS["banks"], ["fields.shock.nodes=[]", "fields.bailout.nodes=[0]"])
    assert bailed.system()[2][0] == pytest.approx(h[0] + s["bailout"]["strength"])


# ---- firms math --------------------------------------------------------------------
def test_grid_edge_count():
    assert len(grid_edges(4, 3)) == 3 * 3 + 4 * 2 == 17


def test_more_money_lowers_h():
    lo, _, _ = prepare(SPECS["firms"], ["fields.money_growth=2"])
    hi, _, _ = prepare(SPECS["firms"], ["fields.money_growth=20"])
    assert np.all(np.array(hi.system()[2]) < np.array(lo.system()[2]))


def test_vat_increase_lowers_h():
    a, _, _ = prepare(SPECS["firms"], ["fields.vat_change=0"])
    b, _, _ = prepare(SPECS["firms"], ["fields.vat_change=5"])
    assert np.all(np.array(b.system()[2]) < np.array(a.system()[2]))


def test_audits_raise_compliance_field():
    a, _, _ = prepare(SPECS["taxpayers"], ["fields.audit_prob=0.01"])
    b, _, _ = prepare(SPECS["taxpayers"], ["fields.audit_prob=0.2"])
    assert b.system()[2][0] > a.system()[2][0]


# ---- end to end through Snigdha's engine -------------------------------------------
@pytest.mark.parametrize("name", list(REGISTRY))
def test_gamma_zero_nothing_moves(name):
    """All terms commute at Gamma = 0: every agent's probability is frozen."""
    r = run_spec(SPECS[name], overrides=FAST + ["uncertainty.gamma=0"])
    P = np.array(r["per_agent"]["p_one"])
    assert np.allclose(P, P[0], atol=1e-10)


@pytest.mark.parametrize("name", list(REGISTRY))
def test_trotter_matches_exact(name):
    r = run_spec(SPECS[name], overrides=["simulation.n_times=5", "simulation.t_max=2.0",
                                         "simulation.steps=16"], exact=True)
    assert r["trotter_max_error"] < 1e-2


@pytest.mark.parametrize("name", list(REGISTRY))
def test_incremental_equals_engine(name):
    """Block-by-block statevector == one circuit per time through the estimator."""
    ov = ["simulation.n_times=5", "simulation.t_max=2.0", "simulation.dt=0.25"]
    a = run_spec(SPECS[name], overrides=ov, method="engine")
    b = run_spec(SPECS[name], overrides=ov, method="incremental")
    assert np.allclose(a["per_agent"]["p_one"], b["per_agent"]["p_one"], atol=1e-10)
    assert a["summary"]["trotter_steps_at_t_max"] == 8


@pytest.mark.parametrize("name", list(REGISTRY))
def test_shipped_specs_accurate_over_full_run(name):
    """Default spec resolution: Trotter vs exact headline error < 1e-2 out to t_max."""
    r = run_spec(SPECS[name], exact=True)
    assert r["trotter_max_error"] < 1e-2


def test_init_state_seed_is_failed():
    r = run_spec(SPECS["banks"], overrides=FAST)
    p0 = r["per_agent"]["p_one"][0]
    assert p0[1] == pytest.approx(1.0) and sum(p0) == pytest.approx(1.0)


def test_shock_causes_excess_failure():
    r = run_spec(SPECS["banks"], overrides=["simulation.n_times=7", "simulation.t_max=3.0",
                                            "simulation.steps=8"], baseline=True)
    excess = np.array(r["excess"]["per_agent"]["p_one"])
    assert excess[:, 0].max() > 0.1      # Core-A is dragged down by Core-B's failure


def test_bailout_reduces_core_a_failure():
    pl, s, _ = prepare(SPECS["banks"])
    pb, _, _ = prepare(SPECS["banks"], ["fields.bailout.nodes=[0]"])
    t = np.linspace(0, 6, 13)
    a = np.array(pl.interpret(t, exact_series(pl, t))["per_agent"]["p_one"])[:, 0]
    b = np.array(pb.interpret(t, exact_series(pb, t))["per_agent"]["p_one"])[:, 0]
    assert b.max() < a.max() / 2


def test_cli_run_writes_json(tmp_path):
    cmd = [sys.executable, "-m", "qecon", "run", SPECS["banks"], "--out", str(tmp_path),
           "--no-plot"] + sum((["--set", o] for o in FAST), [])
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
    data = json.loads((tmp_path / "banks_core_periphery_8.json").read_text())
    assert len(data["times"]) == 4 and len(data["per_agent"]["p_one"][0]) == 8


def test_cli_rejects_bad_spec(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("preset: banks\nagents: {n: 2}\nnetwork: {holdings: [[0, 5, 0.1]]}\n"
                   "fields: {capital_buffer: [10, 10]}\n")
    p = subprocess.run([sys.executable, "-m", "qecon", "validate", str(bad)], cwd=ROOT,
                       capture_output=True, text=True)
    assert p.returncode == 2 and "out of range" in p.stderr
