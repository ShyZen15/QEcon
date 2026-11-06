"""IBM hardware adapter (lottery ticket, not a dependency).

Same spec → same Trotter circuits as the simulator, transpiled for a real device and
run through the Runtime Estimator with error mitigation. Results are cached as JSON in
results/hardware/, where the Streamlit app picks them up automatically (matched by a
hash of the spec, so points only appear when the sliders are at those settings).

One-time setup (you type the token yourself; it is never stored in this repo):
    python -c "from qiskit_ibm_runtime import QiskitRuntimeService as S; S.save_account(token='...', overwrite=True)"
    (check the channel/instance arguments against the current qiskit-ibm-runtime docs)

Commands (from the repo root):
    # dress rehearsal on a FAKE backend: real device noise model, runs locally, free
    python -m backends.hardware fake   specs/banks.yaml --device FakeBoston

    # real hardware: submit, walk away, fetch later
    python -m backends.hardware submit specs/banks.yaml --device ibm_boston
    python -m backends.hardware fetch  results/hardware/<name>.pending.json

    # see what a run would cost before submitting
    python -m backends.hardware plan   specs/banks.yaml --device FakeBoston

Hardware runs use only a few time points and few Trotter steps: every extra two-qubit
gate costs fidelity (signal ~ exp(-N_2q * error)). Defaults: times 0.5, 1.0, 1.5, 2.0,
first order, 1 step per 0.5 time units.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.engine import evolve  # noqa: E402
from qecon.api import exact_series, prepare  # noqa: E402

HW_DIR = os.path.join(ROOT, "results", "hardware")


def spec_hash(spec):
    """Same hash as demo/app.py, so the app can match hardware points to slider settings."""
    clean = {k: v for k, v in spec.items() if not k.startswith("_")}
    return hashlib.sha1(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:12]


def get_device(name):
    """'Fake*' -> local fake backend with a real device's noise model; else IBM Runtime."""
    if name.startswith("Fake"):
        from qiskit_ibm_runtime import fake_provider
        return getattr(fake_provider, name)()
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService().backend(name)


def build(spec_path, overrides, times, dt_hw, order):
    """Logical circuits + observables + metadata. Nothing device-specific yet."""
    plugin, spec, _ = prepare(spec_path, overrides)
    n = plugin.system()[0]
    H = plugin.hamiltonian()
    steps = [max(1, math.ceil(t / dt_hw - 1e-9)) for t in times]
    circuits = [evolve(H, t, s, plugin.init_ones(), order) for t, s in zip(times, steps)]
    obs = plugin.observables(n)
    return plugin, spec, circuits, obs, steps


def transpile_all(circuits, obs, device):
    from qiskit.transpiler import generate_preset_pass_manager
    pm = generate_preset_pass_manager(optimization_level=3, backend=device)
    pubs, stats = [], []
    for qc in circuits:
        isa = pm.run(qc)
        isa_obs = [o.apply_layout(isa.layout) for o in obs]
        pubs.append((isa, isa_obs))
        ops = isa.count_ops()
        twoq = sum(v for k, v in ops.items() if k in ("cz", "cx", "ecr", "rzz"))
        depth2 = isa.depth(lambda ins: ins.operation.num_qubits == 2)
        stats.append({"two_qubit_gates": int(twoq), "two_qubit_depth": int(depth2),
                      "depth": int(isa.depth())})
    return pubs, stats


def make_estimator(device, fake, shots, zne):
    # EstimatorV2 is deprecated since qiskit-ibm-runtime 0.50 (removal >= 3 months later)
    # in favour of the client-side qiskit_ibm_runtime.executor_estimator.Estimator.
    # It still works on 0.51 and its options API is the documented one, so we keep it.
    import warnings
    from qiskit_ibm_runtime import EstimatorV2
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        est = EstimatorV2(mode=device)
    est.options.default_shots = shots
    if not fake:
        # Mitigation only matters on real hardware (local fake runs ignore most of it).
        est.options.resilience_level = 1                      # measurement-error mitigation (TREX)
        if zne:
            est.options.resilience.zne_mitigation = True       # zero-noise extrapolation
        est.options.dynamical_decoupling.enable = True
        est.options.twirling.enable_gates = True
    return est


def package(plugin, spec, times, steps, evs, stds, stats, device_name, kind, order, job_id=None):
    """Same economic interpretation as the simulator, plus the noiseless value of the SAME
    shallow circuit (so the gap you see is hardware noise, not Trotter error) and the
    exact evolution."""
    out = plugin.interpret(np.array(times), np.array(evs))
    ideal = plugin.interpret(np.array(times), exact_series_trotter(plugin, times, steps, order))
    exact = plugin.interpret(np.array(times), exact_series(plugin, np.array(times)))
    key = plugin.headline
    std_M = np.array(stds)[:, 0]
    sign = 1 if plugin.headline_from_zero else -1
    return {
        "preset": spec["preset"], "name": spec.get("name"), "spec_hash": spec_hash(spec),
        "kind": kind, "backend": device_name, "job_id": job_id,
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "times": list(map(float, times)), "trotter_steps": steps, "order": order,
        "series": out["series"], "per_agent": out["per_agent"],
        "stds": {key: (np.abs(sign) * std_M / 2).tolist()},
        "ideal_same_circuit": {key: ideal["series"][key]},
        "exact": {key: exact["series"][key]},
        "circuit_stats": stats,
    }


def exact_series_trotter(plugin, times, steps, order):
    """Noiseless statevector of the exact same (logical) circuits."""
    from qiskit.quantum_info import Statevector
    H = plugin.hamiltonian()
    obs = plugin.observables(plugin.system()[0])
    rows = []
    for t, s in zip(times, steps):
        psi = Statevector(evolve(H, t, s, plugin.init_ones(), order))
        rows.append([float(psi.expectation_value(o).real) for o in obs])
    return np.array(rows)


def save(data, stem):
    os.makedirs(HW_DIR, exist_ok=True)
    path = os.path.join(HW_DIR, f"{stem}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    return path


def report(data):
    key = next(iter(data["ideal_same_circuit"]))
    print(f"{'t':>5} {'steps':>5} {'2q gates':>8} {'2q depth':>8} {'device':>8} {'ideal':>8} {'exact':>8}")
    for k, t in enumerate(data["times"]):
        s = data["circuit_stats"][k]
        print(f"{t:5.2f} {data['trotter_steps'][k]:5d} {s['two_qubit_gates']:8d} "
              f"{s['two_qubit_depth']:8d} {data['series'][key][k]:8.3f} "
              f"{data['ideal_same_circuit'][key][k]:8.3f} {data['exact'][key][k]:8.3f}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="backends.hardware")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("fake", "submit", "plan"):
        q = sub.add_parser(name)
        q.add_argument("spec")
        q.add_argument("--device", default="FakeBoston" if name != "submit" else None,
                       required=name == "submit")
        q.add_argument("--times", default="0.5,1.0,1.5,2.0")
        q.add_argument("--dt", type=float, default=0.5, help="Trotter step size on hardware")
        q.add_argument("--order", type=int, default=1, choices=[1, 2])
        q.add_argument("--shots", type=int, default=4096)
        q.add_argument("--no-zne", action="store_true")
        q.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    f = sub.add_parser("fetch")
    f.add_argument("pending")
    args = p.parse_args(argv)

    if args.cmd == "fetch":
        with open(args.pending, encoding="utf-8") as fh:
            pend = json.load(fh)
        from qiskit_ibm_runtime import QiskitRuntimeService
        job = QiskitRuntimeService().job(pend["job_id"])
        print("status:", job.status())
        res = job.result()
        evs = [np.atleast_1d(r.data.evs) for r in res]
        stds = [np.atleast_1d(r.data.stds) for r in res]
        times = pend["times"]
        plugin, spec, _, _, steps = build(pend["spec"], pend["overrides"], times,
                                          pend["dt"], pend["order"])
        data = package(plugin, spec, times, steps, evs, stds, pend["circuit_stats"],
                       pend["backend"], "hardware", pend["order"], pend["job_id"])
        print("wrote", save(data, pend["stem"]))
        report(data)
        return 0

    times = [float(x) for x in args.times.split(",")]
    plugin, spec, circuits, obs, steps = build(args.spec, args.set, times, args.dt, args.order)
    device = get_device(args.device)
    pubs, stats = transpile_all(circuits, obs, device)
    total = sum(s["two_qubit_gates"] for s in stats)
    print(f"{spec.get('name')} on {args.device}: {plugin.system()[0]} qubits, "
          f"2q gates per circuit {[s['two_qubit_gates'] for s in stats]}, "
          f"2q depth {[s['two_qubit_depth'] for s in stats]}")
    worst = max(s["two_qubit_gates"] for s in stats)
    print(f"rough signal kept at the deepest circuit, exp(-N*3e-3): {math.exp(-worst * 3e-3):.0%}")
    if args.cmd == "plan":
        return 0

    stem = f"{spec.get('name')}_{args.device}"
    if args.cmd == "fake":
        est = make_estimator(device, True, args.shots, False)
        res = est.run(pubs).result()
        evs = [np.atleast_1d(r.data.evs) for r in res]
        stds = [np.atleast_1d(r.data.stds) for r in res]
        data = package(plugin, spec, times, steps, evs, stds, stats, args.device,
                       "noisy simulator, not hardware", args.order)
        print("wrote", save(data, stem))
        report(data)
        return 0

    # submit to real hardware
    est = make_estimator(device, False, args.shots, not args.no_zne)
    job = est.run(pubs)
    pend = {"job_id": job.job_id(), "backend": args.device, "spec": os.path.abspath(args.spec),
            "overrides": args.set, "times": times, "dt": args.dt, "order": args.order,
            "circuit_stats": stats, "stem": stem,
            "submitted": dt.datetime.now().isoformat(timespec="seconds")}
    os.makedirs(HW_DIR, exist_ok=True)
    path = os.path.join(HW_DIR, f"{stem}.pending.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pend, fh, indent=1)
    print(f"submitted job {job.job_id()} -> {path}")
    print(f"fetch later with:  python -m backends.hardware fetch {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
