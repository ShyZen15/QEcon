# Live demo & hardware (Person 4 workstream)

## Run the demo

```bash
pip install -r requirements-demo.txt
streamlit run demo/app.py            # from the repo root -> http://localhost:8501
```

The demo runs on the local statevector simulator, so it can't fail on stage. Every slider change re-compiles the Hamiltonian and re-simulates the Trotter circuits (≈0.1 s firms/taxpayers, ≈1 s banks; results are cached).

| Panel | What it shows |
|---|---|
| Sidebar | Economy picker; policy sliders bound to the YAML spec (`fields.*`); Γ slider; toggles for the no-shock baseline, the exact matrix-exponential overlay, and hardware points |
| Metrics | agents (qubits), ZZ edges, peak of the headline, exact-simulation memory 16·2ⁿ, two-qubit gates per Trotter step, and Δ vs the counterfactual |
| **Dynamics** | headline curve (current policy vs counterfactual vs exact, plus hardware diamonds if cached); **animated network**: node colour = P(state 1), opens at the peak moment, ▶ Play animates it |
| **Light-cone** | heatmap, agents sorted by graph distance from the seed × time; side by side with the counterfactual (e.g. without the bailout) |
| The Hamiltonian | the formula, a table of h_i, Γ_i and starting state per agent, a table of J_ij per edge, and sources |
| Spec & validator | the live YAML the sliders are editing. Edit it, press **Run spec**; a bad spec shows every validator error at once |

Counterfactuals: banks with a bailout → "without the bailout"; firms off-target → "money growth on target, no tax change".

**Windows note:** on laptops with Smart App Control, one of pandas' DLLs can be blocked. The app detects that and runs without pandas, so nothing to do.

## 3-minute demo script

1. **Banks** (default). *"Core-B, a money-center bank, fails. Blue: share of banks insolvent. Green: the same economy with no shock, i.e. pure Γ-noise. The gap is contagion."* Point at the network: Core-B outlined; Core-A and Core-C going blue.
2. **Bail out → Core-A.** *"A bailout is just an extra field on one qubit."* Metric shows the peak dropping; orange = without the bailout. Open **Light-cone**: Core-A's row goes white.
3. **Γ → 0.** *"Turn off the transverse field."* The curves go flat, and the app warns that every term commutes and nothing moves. *"Uncertainty is the engine. Without it this is a classical, frozen model."* Put Γ back to 0.6.
4. **Firms.** Drag **money growth** 2 → 20 %. *"Expectations stay anchored, then de-anchor abruptly."* The grid turns blue.
5. **Spec & validator.** *"Every slider edits this YAML; each number has a source comment. Break it…"* (type a bad index) → validator lists the problems.
6. If hardware JSON exists: back to Banks with default sliders → yellow diamonds on the curve.

## Hardware (lottery ticket, not a dependency)

The app overlays any `results/hardware/*.json` whose spec hash matches the current sliders (default settings), and silently skips otherwise.

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
