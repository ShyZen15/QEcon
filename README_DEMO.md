# Live demo & hardware (Person 4 workstream)

There are two frontends over one backend. Both call `demo.server.api_run`, so levers, counterfactuals and hardware matching are the same code.

| Frontend | Use it for | Run |
|---|---|---|
| Streamlit app (`demo/streamlit_app.py`) | The public link | `streamlit run demo/streamlit_app.py` |
| Hand-built web demo (`demo/web/`) | On stage: works offline, no CDN | `python -m demo.server` |

## Deploy to Streamlit Community Cloud

1. Sign in at [share.streamlit.io](https://share.streamlit.io) with the GitHub account that administers this repo.
2. Choose **Create app**, then deploy from the repo.
3. Set the repository to `ShyZen15/Quantum-larpers`, pick the branch, and set the main file path to `demo/streamlit_app.py`.
4. Under **Advanced settings**, choose Python 3.13 if it's offered. That's the version this was tested on.
5. Press **Deploy**.

Cloud reads `demo/requirements.txt` first because it sits next to the entrypoint, so it installs only what the app needs. `.streamlit/config.toml` stays at the repo root, as Cloud requires.

Measured in a clean environment built from that file: 189 MB peak memory, against Cloud's published 690 MB–2.7 GB range. Apps sleep after 12 hours without traffic, so open the link before you need it. The spec editor has tighter limits than the command line (14 agents, 61 time points, t ≤ 30, 600 Trotter steps), because everyone shares one small machine.

## Run the hand-built web demo

```bash
pip install -r requirements.txt
python -m demo.server                # from the repo root -> http://localhost:8501
```

A small standard-library server (`demo/server.py`) wraps `qecon.api.run_spec` in a JSON API. The front end (`demo/web/`: plain HTML, CSS and hand-drawn SVG, no frameworks, no CDN) works fully offline. Everything runs on the local statevector simulator, so it can't fail on stage. A lever move takes about 0.3–0.7 s (each run also computes the exact reference and the counterfactual), cached after the first time.

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

The demo overlays any `results/hardware/*.json` whose *physics* fingerprint (`qecon.api.physics_hash`: agents, network, fields, Γ, initial state) matches the current levers, i.e. the defaults, and silently skips otherwise. Simulator settings such as Trotter order don't affect the match. A test (`tests/test_integration.py`) fails if the cached run ever stops matching the default bank spec.

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

Use **banks** for hardware: 8 qubits, 27–115 two-qubit gates after transpiling for FakeBoston (transpiler seeded, so the counts are reproducible; ≈71% signal kept at the deepest circuit). Firms (12 qubits) needs 74–316 two-qubit gates, and that few Trotter steps is already far from exact, so it's not worth the queue.

The fetched JSON also stores `ideal_same_circuit` (noiseless value of the *same shallow* circuit) and `exact`. Then on stage you can separate hardware noise (device vs ideal) from Trotter error (ideal vs exact).

Fake-backend rehearsal for banks (`results/hardware/banks_core_periphery_8_FakeBoston.json`, labelled "noisy simulator, not hardware" in the app):

| t | steps | 2q gates | 2q depth | noisy sim | ideal (same circuit) | exact |
|---|---|---|---|---|---|---|
| 0.5 | 1 | 27 | 18 | 0.194 | 0.190 | 0.184 |
| 1.0 | 2 | 58 | 47 | 0.304 | 0.307 | 0.296 |
| 1.5 | 3 | 85 | 67 | 0.401 | 0.396 | 0.381 |
| 2.0 | 4 | 115 | 90 | 0.415 | 0.410 | 0.394 |

Notes: `qiskit_ibm_runtime.EstimatorV2` is deprecated since 0.50 (removal ≥ 3 months later) in favour of the client-side `executor_estimator.Estimator`; it still works on 0.51. Check the `save_account` channel/instance arguments against the current docs.
