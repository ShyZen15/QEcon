"""One function for everything: the CLI and the Streamlit app both call run_spec().

    from qecon.api import run_spec
    result = run_spec("specs/banks.yaml")                         # path ...
    result = run_spec(spec_dict, overrides=["fields.bailout.nodes=[1]"])   # ... or dict

The returned dict is JSON-serializable (see RESULT SHAPE in README_PLUGINS.md).
"""
import copy
import json
import os
import time

import numpy as np
from qiskit.quantum_info import Statevector

from core.engine import exact_state
from plugins import REGISTRY

from .spec import apply_overrides, load_spec, validate

EXACT_MAX_AGENTS = 16


def prepare(spec_or_path, overrides=None):
    """Load + override + validate. Returns (plugin, spec, warnings). No circuits yet."""
    spec = load_spec(spec_or_path) if isinstance(spec_or_path, (str, os.PathLike)) \
        else copy.deepcopy(spec_or_path)
    spec = apply_overrides(spec, overrides)
    spec, warns = validate(spec)
    return REGISTRY[spec["preset"]](spec), spec, warns


def exact_series(plugin, times):
    """Same observables, computed by sparse matrix exponential instead of circuits."""
    n = plugin.system()[0]
    H = plugin.hamiltonian()
    obs = [o.to_matrix(sparse=True) for o in plugin.observables(n)]
    rows = []
    for t in times:
        psi = exact_state(H, float(t), plugin.init_ones())
        rows.append([float(np.real(np.vdot(psi, O @ psi))) for O in obs])
    return np.array(rows)


def run_spec(spec_or_path, backend=None, overrides=None, exact=False, baseline=False):
    t0 = time.perf_counter()
    plugin, spec, warns = prepare(spec_or_path, overrides)
    sim = spec["simulation"]
    times = np.linspace(0.0, float(sim["t_max"]), int(sim["n_times"]))

    raw = plugin.run(times, steps=int(sim["steps"]), backend=backend or sim["backend"],
                     order=int(sim["order"]))
    evs = np.vstack([np.atleast_1d(r) for r in raw])
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
        "summary": plugin.gate_summary(),
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
                        overrides=plugin.baseline_overrides())
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
