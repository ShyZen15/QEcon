# Live demo & hardware (Person 4 workstream)

## Run the demo

```bash
pip install -r requirements-demo.txt
python -m demo.server                # from the repo root -> http://localhost:8501
```

A small standard-library server (`demo/server.py`) wraps `qecon.api.run_spec` in a JSON API. The front end (`demo/web/`: plain HTML, CSS and hand-drawn SVG, no frameworks, no CDN) works fully offline. Everything runs on the local statevector simulator, so it can't fail on stage. A lever move takes about 0.3–0.7 s, cached after the first time.

| Area | What it shows |
|---|---|
| Top bar | scenario switch (Contagion · Inflation · Compliance), engine status, **light/dark toggle** (remembered; defaults to the system setting) |
| Lever rail | the levers for the scenario, grouped (Shock / Policy / Uncertainty). **Show terms** reveals the Hamiltonian term each lever edits, e.g. `h = 0.05 × (CET1 − 7%)` |
| Headline + stats | one sentence rewritten from the numbers on every run, then four stat cards (peak, effect vs the counterfactual, most exposed / propagation speed, policy effect) |
| View bar | **Dynamics · Light-cone · Model** tabs, plus the shared clock (▶, scrubber; Space / ← → on the keyboard) |
| Dynamics | the time chart (current vs counterfactual vs background, exact dotted, device diamonds) next to the network (colour and % = P(state 1) at the clock time) |
| Light-cone | agents × time heatmaps sorted by distance from the shock, current policy next to the comparison |
| Model | the Hamiltonian and term-by-term mapping; cost (qubits, 16·2ⁿ memory, gates/step) and accuracy; sources |
| View spec | the YAML in a side sheet; edit it, then **Validate & run** lists every validator error |

Counterfactuals: banks → no-shock background, plus "same shock, no bailout" when a bank is bailed out; firms → money growth on target; taxpayers → no evader cluster.

## 3-minute demo script

1. **Contagion** (default). Read the headline aloud: *"When Core-B fails, up to 45% of the banking system is insolvent, 2× the background rate."* Point at the green line: *"that's the same economy with no shock, i.e. pure Γ-noise. The gap is contagion."*
2. **Bail out → Core-A.** The headline rewrites itself. The stats show −8 pts, the network gets a dashed ring, and the light-cone's Core-A row goes pale next to the unchecked one.
3. **Γ → 0.** *"Turn off the one non-commuting term."* Everything freezes, and the headline says why. *"Uncertainty is the engine."* Put Γ back.
4. **Inflation.** Drag money growth 2 → 20%: *"anchored… anchored… de-anchored"*. Press ▶ and watch the grid fill in.
5. **View spec.** *"Every lever edits this file, and every number has a source."* Break an index → Validate & run → the validator lists every problem.
6. **Under the hood** (scroll): 16·2ⁿ memory vs gates per step, max error vs exact, and the sources.

## Hardware (lottery ticket, not a dependency)

The demo overlays any `results/hardware/*.json` whose spec hash matches the current levers (i.e. the defaults), and silently skips otherwise.

```bash
# 0. one-time: save your IBM Quantum token yourself (never commit it)
python -c "from qiskit_ibm_runtime import QiskitRuntimeService as S; S.save_account(token='PASTE', overwrite=True)"

# 1. rehearse for free on a fake backend with a real device's noise model (already done for banks)
python -m backends.hardware fake specs/banks.yaml --device FakeBoston

# 2. see the cost on the real device (transpiled gate counts, no job submitted)
python -m backends.hardware plan specs/banks.yaml --device ibm_boston

# 3. submit, walk away; fetch when done (cached to results/hardware/)
python -m backends.hardware submit specs/banks.yaml --device ibm_boston
python -m backends.hardware fetch results/hardware/banks_core_periphery_8_ibm_boston.pending.json
```

Defaults: t = 0.5, 1.0, 1.5, 2.0; first-order Trotter, 1 step per 0.5 time units; 4096 shots; TREX + ZNE, dynamical decoupling, gate twirling. **One Estimator job, 4 circuits**, well inside the free 10-minute window.

Use **banks** for hardware: 8 qubits, 27–109 two-qubit gates after transpiling for FakeBoston (≈72% signal kept at the deepest circuit). Firms (12 qubits) needs 74–316 two-qubit gates, and that few Trotter steps is already far from exact, so it's not worth the queue.

The fetched JSON also stores `ideal_same_circuit` (noiseless value of the *same shallow* circuit) and `exact`. Then on stage you can separate hardware noise (device vs ideal) from Trotter error (ideal vs exact).

Fake-backend rehearsal for banks (`results/hardware/banks_core_periphery_8_FakeBoston.json`, labelled "noisy simulator, not hardware" in the app):

| t | steps | 2q gates | 2q depth | noisy sim | ideal (same circuit) | exact |
|---|---|---|---|---|---|---|
| 0.5 | 1 | 27 | 21 | 0.190 | 0.190 | 0.184 |
| 1.0 | 2 | 57 | 46 | 0.311 | 0.307 | 0.296 |
| 1.5 | 3 | 77 | 57 | 0.396 | 0.396 | 0.381 |
| 2.0 | 4 | 109 | 62 | 0.418 | 0.410 | 0.394 |

Notes: `qiskit_ibm_runtime.EstimatorV2` is deprecated since 0.50 (removal ≥ 3 months later) in favour of the client-side `executor_estimator.Estimator`; it still works on 0.51. Check the `save_account` channel/instance arguments against the current docs.
