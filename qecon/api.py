"""One function for everything: the CLI and both demos call run_spec().

    from qecon.api import run_spec
    result = run_spec("specs/banks.yaml")                         # path ...
    result = run_spec(spec_dict, overrides=["fields.bailout.nodes=[1]"])   # ... or dict

The returned dict is JSON-serializable (see RESULT SHAPE in README_PLUGINS.md).
"""
import copy
import json
import math
import os
import time

import numpy as np
from qiskit.quantum_info import Statevector

from core.engine import evolve, exact_state, get_estimator
from plugins import REGISTRY

from .spec import SpecError, apply_overrides, load_spec, validate

EXACT_MAX_AGENTS = 16


PHYSICS_KEYS = ("preset", "agents", "network", "fields", "uncertainty", "initial")


def physics_hash(spec):
    """Fingerprint of the MODEL (who, links, fields, Gamma, initial state), ignoring
    simulator settings, names and sources. Used to match cached hardware runs to the
    demo's current levers, so changing e.g. Trotter order doesn't orphan them."""
    import hashlib
    core = {k: spec.get(k) for k in PHYSICS_KEYS}
    return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:12]


def prepare(spec_or_path, overrides=None):
    """Load + override + validate. Returns (plugin, spec, warnings). No circuits yet."""
    spec = load_spec(spec_or_path) if isinstance(spec_or_path, (str, os.PathLike)) \
        else copy.deepcopy(spec_or_path)
    spec = apply_overrides(spec, overrides)
    spec, warns = validate(spec)
    return REGISTRY[spec["preset"]](spec), spec, warns


def exact_series(plugin, times):
    """Same observables, computed by sparse matrix exponential instead of circuits.
    On a uniform grid, SciPy steps exp(-iHt)|psi0> across all times in one call
    (same result as core.engine.exact_state at each t, several times faster)."""
    from scipy.sparse.linalg import expm_multiply
    n = plugin.system()[0]
    H = plugin.hamiltonian()
    obs = [o.to_matrix(sparse=True) for o in plugin.observables(n)]
    T = np.asarray(times, dtype=float)
    uniform = len(T) > 2 and np.allclose(np.diff(T), T[1] - T[0])
    if uniform:
        psi0 = Statevector.from_int(sum(1 << q for q in plugin.init_ones()), 2 ** n).data
        A = (-1j * H.to_matrix(sparse=True)).tocsc()
        states = expm_multiply(A, psi0, start=T[0], stop=T[-1], num=len(T), endpoint=True)
    else:
        states = [exact_state(H, float(t), plugin.init_ones()) for t in T]
    return np.array([[float(np.real(np.vdot(psi, O @ psi))) for O in obs] for psi in states])


def trotter_schedule(sim, times):
    """Trotter steps for each time point.

    With simulation.dt (preferred): the gap between time points is split into
    m = ceil(gap / dt) steps, and time t_k gets k*m steps. Every circuit then has
    the same step size (<= dt), so late times are not under-resolved, AND the circuit
    for t_k is exactly the circuit for t_(k-1) followed by m more identical steps.
    Without dt: the legacy fixed simulation.steps for every time.
    Returns (steps_per_time, m or None)."""
    if sim.get("dt"):
        gap = float(times[1] - times[0])
        m = max(1, math.ceil(gap / float(sim["dt"]) - 1e-9))
        return [k * m for k in range(len(times))], m
    return [int(sim["steps"])] * len(times), None


def simulate_engine(plugin, times, steps, order, backend):
    """One circuit per time (Snigdha's evolve), one batched estimator call."""
    H = plugin.hamiltonian()
    obs = plugin.observables(plugin.system()[0])
    circuits = [evolve(H, float(t), max(1, s), plugin.init_ones(), order)
                for t, s in zip(times, steps)]
    res = get_estimator(backend).run([(qc, obs) for qc in circuits]).result()
    return np.vstack([np.atleast_1d(r.data.evs) for r in res])


def simulate_incremental(plugin, times, m, order):
    """The SAME Trotter circuits, simulated block by block: the state at t_k is the
    state at t_(k-1) pushed through one block evolve(H, gap, m). Identical to
    simulate_engine (tested to 1e-10) but ~T/2 times cheaper. Statevector only."""
    H = plugin.hamiltonian()
    n = plugin.system()[0]
    obs = plugin.observables(n)
    gap = float(times[1] - times[0])
    block = evolve(H, gap, m, (), order)
    psi = Statevector.from_int(sum(1 << q for q in plugin.init_ones()), 2 ** n)
    rows = []
    for k in range(len(times)):
        if k:
            psi = psi.evolve(block)
        rows.append([float(psi.expectation_value(o).real) for o in obs])
    return np.array(rows)


def run_spec(spec_or_path, backend=None, overrides=None, exact=False, baseline=False,
             method="auto"):
    """method: 'engine' (one circuit per time through the estimator), 'incremental'
    (same circuits, block-by-block statevector; needs simulation.dt and a local
    backend), or 'auto' (incremental when possible)."""
    t0 = time.perf_counter()
    plugin, spec, warns = prepare(spec_or_path, overrides)
    sim = spec["simulation"]
    times = np.linspace(0.0, float(sim["t_max"]), int(sim["n_times"]))
    backend = backend or sim["backend"]
    if backend != "local":
        raise SpecError(f"backend {backend!r} is not available in run_spec: real-hardware "
                        "runs go through python -m backends.hardware")
    steps, m = trotter_schedule(sim, times)
    if method == "auto":
        method = "incremental" if (m is not None and backend == "local") else "engine"
    if method == "incremental":
        if m is None:
            raise ValueError("incremental simulation needs simulation.dt")
        evs = simulate_incremental(plugin, times, m, int(sim["order"]))
    else:
        evs = simulate_engine(plugin, times, steps, int(sim["order"]), backend)
    out = plugin.interpret(times, evs)

    n, edges, h, gamma = plugin.system()
    result = {
        "preset": spec["preset"],
        "name": spec.get("name", spec["preset"]),
        "times": times.tolist(),
        "labels": plugin.labels(),
        "states": {"0": plugin.state_names[0], "1": plugin.state_names[1]},
        "headline": plugin.headline,
        "headline_label": plugin.headline_label,
        "series": out["series"],
        "per_agent": out["per_agent"],
        "graph": {
            "n": n,
            "edges": [[i, j, J] for (i, j), J in sorted(edges.items())],
            "h": list(h),
            "gamma": list(gamma),
            "init_ones": list(plugin.init_ones()),
            "positions": {str(k): v for k, v in plugin.positions().items()},
            "distance_from_seed": plugin.distance_from_seed(),
        },
        "summary": {**plugin.gate_summary(), "method": method,
                    "trotter_steps_at_t_max": int(steps[-1]),
                    "trotter_dt": float(times[-1] / steps[-1]) if steps[-1] else None},
        "warnings": warns,
        "sources": spec.get("sources", {}),
        "spec": {k: v for k, v in spec.items() if not k.startswith("_")},
    }
    if exact and n <= EXACT_MAX_AGENTS:
        ex = plugin.interpret(times, exact_series(plugin, times))
        result["exact"] = ex
        result["trotter_max_error"] = float(np.max(np.abs(
            np.array(out["series"][plugin.headline]) - np.array(ex["series"][plugin.headline]))))
    if baseline:
        base = run_spec(result["spec"], backend=backend,
                        overrides=plugin.baseline_overrides(), method=method)
        key = plugin.headline
        result["baseline"] = {"series": base["series"], "per_agent": base["per_agent"],
                              "overrides": plugin.baseline_overrides()}
        result["excess"] = {
            "series": {key: (np.array(out["series"][key]) - np.array(base["series"][key])).tolist()},
            "per_agent": {"p_one": (np.array(out["per_agent"]["p_one"])
                                    - np.array(base["per_agent"]["p_one"])).tolist()},
        }
    result["runtime_s"] = round(time.perf_counter() - t0, 3)
    return result


def save_result(result, out_dir="out", stem=None):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{stem or result['name']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    return path


def load_result(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
