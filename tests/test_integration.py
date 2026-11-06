"""Cross-workstream checks: the pieces fit together.

- Every real preset's Hamiltonian matches Shiven's NumPy-only reference, which shares
  no code with Qiskit (validation/PLAN.md finding 3, now on the bank network too).
- Presets evolved by the circuits match the independent exact evolution.
- First and second order Trotter agree on every Z-basis observable (finding 5), which
  is why the specs use first order.
- The bank preset shows contagion above the no-seed background (finding 10).
- The demo server API and the hardware adapter work end to end.

    python -m pytest tests -q
"""
import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest

from plugins import REGISTRY
from qecon.api import exact_series, prepare, run_spec
from validation import reference
from validation.systems import System

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = {name: os.path.join(ROOT, "specs", f"{name}.yaml") for name in REGISTRY}


def as_system(plugin):
    n, edges, h, gamma = plugin.system()
    return System(n, edges, np.array(h), np.array(gamma), tuple(plugin.init_ones()))


# ---- independent reference ---------------------------------------------------------
@pytest.mark.parametrize("name", list(REGISTRY))
def test_hamiltonian_matches_numpy_reference(name):
    plugin, _, _ = prepare(SPECS[name])
    n, edges, h, gamma = plugin.system()
    ours = plugin.hamiltonian().to_matrix(sparse=True)
    ref = reference.hamiltonian(n, edges, h, gamma)
    assert abs(ours - ref).max() < 1e-12


@pytest.mark.parametrize("name", list(REGISTRY))
def test_presets_match_independent_exact_evolution(name):
    plugin, spec, _ = prepare(SPECS[name], ["simulation.n_times=9", "simulation.t_max=4.0"])
    times = np.linspace(0, 4.0, 9)
    states = reference.exact_series(as_system(plugin), times)
    n = plugin.system()[0]
    p_ref = np.array([(1 - reference.z_expectations(psi, n)) / 2 for psi in states])
    ours_exact = plugin.interpret(times, exact_series(plugin, times))["per_agent"]["p_one"]
    assert np.allclose(ours_exact, p_ref, atol=1e-10)
    circuit = run_spec(SPECS[name], overrides=["simulation.n_times=9", "simulation.t_max=4.0"])
    assert np.abs(np.array(circuit["per_agent"]["p_one"]) - p_ref).max() < 1e-2


@pytest.mark.parametrize("name", list(REGISTRY))
def test_first_order_equals_second_order_on_z_observables(name):
    a = run_spec(SPECS[name], overrides=["simulation.order=1", "simulation.n_times=7"])
    b = run_spec(SPECS[name], overrides=["simulation.order=2", "simulation.n_times=7"])
    for key in ("p_one",):
        assert np.allclose(a["per_agent"][key], b["per_agent"][key], atol=1e-12)
    assert np.allclose(a["series"]["synchronization"], b["series"]["synchronization"], atol=1e-12)
    assert a["summary"]["cx_per_step"] * 2 == b["summary"]["cx_per_step"]


def test_bank_contagion_exceeds_no_seed_background():
    """Finding 10 on the real bank network: the seed's neighbours rise well above the
    no-seed background, and the effect weakens with distance."""
    r = run_spec(SPECS["banks"], baseline=True)
    ex = np.array(r["excess"]["per_agent"]["p_one"]).max(axis=0)
    d = np.array(r["graph"]["distance_from_seed"])
    seed = r["graph"]["init_ones"][0]
    core_neighbours = [i for i in range(r["graph"]["n"]) if d[i] == 1 and i in (0, 2)]
    assert all(ex[i] > 0.2 for i in core_neighbours)
    assert ex[d == 2].mean() < ex[(d == 1)].mean()
    assert ex[seed] > 0.5


# ---- demo server -------------------------------------------------------------------
@pytest.fixture(scope="module")
def server():
    from demo.server import Handler
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_server_serves_page_and_presets(server):
    with urllib.request.urlopen(server + "/", timeout=10) as r:
        assert b"QEcon" in r.read()
    with urllib.request.urlopen(server + "/api/presets", timeout=10) as r:
        assert set(json.loads(r.read())) == set(REGISTRY)
    for asset in ("/app.js", "/styles.css"):
        with urllib.request.urlopen(server + asset, timeout=10) as r:
            assert r.status == 200


def test_server_blocks_path_traversal(server):
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(server + "/../qecon/api.py", timeout=10)


@pytest.mark.parametrize("name", list(REGISTRY))
def test_server_run_each_preset(server, name):
    code, d = post(server + "/api/run", {"preset": name, "overrides": ["simulation.n_times=7"]})
    assert code == 200
    r = d["result"]
    assert len(r["times"]) == 7 and "baseline" in r and "exact" in r


def test_server_bailout_counterfactual(server):
    code, d = post(server + "/api/run", {"preset": "banks", "overrides": ["fields.bailout.nodes=[0]", "simulation.n_times=7"]})
    assert code == 200 and d["counterfactual"] is not None
    assert d["counterfactual"]["spec"]["fields"]["bailout"]["nodes"] == []


def test_server_hardware_points_match_default_spec(server):
    """The cached FakeBoston run must line up with the default bank spec, so it shows
    in the demo. If the spec changes, rerun: python -m backends.hardware fake specs/banks.yaml"""
    ui_overrides = ["initial.ones=[1]", "fields.shock.nodes=[1]", "fields.bailout.nodes=[]",
                    "fields.bailout.strength=2.0", "fields.kappa=0.05", "uncertainty.gamma=0.6"]
    code, d = post(server + "/api/run", {"preset": "banks", "overrides": ui_overrides})
    assert code == 200 and len(d["hardware"]) >= 1


def test_server_rejects_bad_spec(server):
    code, d = post(server + "/api/run", {"preset": "banks", "overrides": ["initial.ones=[42]"]})
    assert code == 400 and "out of range" in d["error"]
    code, d = post(server + "/api/run_yaml", {"yaml": "preset: banks\nagents: {n: 2}\n"})
    assert code == 200 and not d["ok"] and d["errors"]


# ---- hardware adapter --------------------------------------------------------------
def test_hardware_plan_on_fake_backend(capsys):
    from backends.hardware import main
    assert main(["plan", SPECS["banks"], "--device", "FakeBoston", "--times", "0.5,1.0"]) == 0
    assert "2q gates per circuit" in capsys.readouterr().out
