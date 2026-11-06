# QEcon: economic policy as a quantum Hamiltonian

**Live app:** https://qecon-q.streamlit.app

QEcon compiles an economic interaction network into a transverse-field Ising Hamiltonian and simulates its coherent dynamics with Qiskit Trotter circuits:

```
H = −Σ J_ij Z_i Z_j  −  Σ h_i Z_i  −  Σ Γ_i X_i
     interactions      policy & fundamentals   uncertainty (the only non-commuting term)
```

Each agent (a bank, a firm, a taxpayer) is a qubit: |0⟩ = solvent / hold / comply, |1⟩ = insolvent / raise price / evade. Exposures and imitation become ZZ couplings, and policy levers become fields. The transverse field Γ (uncertainty) is the one ingredient that makes the model quantum: at Γ = 0 every term commutes and nothing moves.

**What we claim, and what we don't.** We claim a working, validated compiler from a domain spec to a circuit. For this coherent model, exact classical simulation needs 16·2ⁿ bytes, while the circuit cost grows linearly with the number of interactions. We do **not** claim better economic forecasts, a speedup over classical econophysics (those models are classical Monte Carlo), or that people or economies are physically quantum. The full list is in `SLIDES_ISHA.md` → "What we do NOT claim".

## The pipeline

```
specs/*.yaml ─▶ qecon.spec (validate) ─▶ plugins/*  ─▶ core.engine.compile_ising ─▶ evolve (Trotter)
  domain spec     every error at once     J, h, Γ       SparsePauliOp                 circuits
                                                                                          │
   demo/ (live UI) ◀── qecon.api.run_spec ◀── interpret ◀── StatevectorEstimator ◀────────┘
   backends/ (IBM hardware)                   economic observables
   validation/ (independent checks: NumPy-only H, exact evolution, Glauber baseline)
```

## Quick start

```bash
pip install -r requirements.txt

streamlit run demo/streamlit_app.py          # live demo, the same app that deploys to Streamlit
python -m demo.server                        # hand-built web demo -> http://localhost:8501
python -m qecon run specs/banks.yaml         # one preset from the command line -> out/*.json + .png
python -m pytest -q                          # all tests
python -m qecon.figures                      # preset figures for the deck -> figures/
python -m validation.run_all                 # validation figures -> validation/figures/
python tools/build_notebook.py               # rebuild and run QEcon_submission.ipynb
```

Run everything from the repo root.

**`QEcon_submission.ipynb` is the whole project in one file.** It embeds every module, spec and test unchanged, so it runs on its own with no repo: open it and use Run All. `tests/test_notebook.py` fails if it drifts from the repo, so rebuild it after changing code.

## Repository map

| Workstream | Where | Docs |
|---|---|---|
| **Engine**: `compile_ising`, `evolve`, `exact_state`, `run_time_series`, `Plugin` base class | `core/engine.py` | `use_it.py`, `plugin_demo.py`, `steps_check.py`, `bench.py` are small worked examples |
| **Validation**: Trotter convergence, memory wall, entanglement entropy, Glauber Monte Carlo, observable error; NumPy-only reference | `validation/` | `validation/PLAN.md` (findings 1–10), `validation/validation.ipynb` |
| **Plugins & DSL**: YAML specs, validator, three presets, CLI, `run_spec` API | `plugins/`, `specs/`, `qecon/` | `README_PLUGINS.md`, `CITATIONS.md`, `SLIDES_ISHA.md` |
| **Demo & hardware**: Streamlit app and hand-built web demo (both call `demo.server.api_run`); IBM adapter (plan / fake / submit / fetch) | `demo/`, `backends/` | `README_DEMO.md` (includes the 3-minute demo script and deployment), `SLIDES_ARSH.md` |
| **Submission**: the whole project as one notebook | `QEcon_submission.ipynb`, `tools/build_notebook.py` | |
| Tests | `validation/test_engine.py`, `tests/` | `tests/test_integration.py` ties the workstreams together |
| Outputs | `figures/` and `results/` (presets), `validation/figures/`, `results/hardware/` | |

## Presets

| Scenario | Agents | J (ZZ) | h (Z) | Headline result |
|---|---|---|---|---|
| **Contagion** `specs/banks.yaml` | 8 banks, core–periphery, 9 links | symmetrised Elliott–Golub–Jackson dependency | Basel III capital buffer, shock, bailout | When Core-B fails, peak insolvency reaches 45% vs 22% with no shock. Bailing out Core-A cuts its own peak failure from ~47% to ~10%. |
| **Inflation** `specs/firms.yaml` | 12 firms, 4×3 supply grid | strategic complementarity in pricing | credibility, money growth, VAT | Expectations stay anchored, then de-anchor: peak share raising prices ≈5% at 2% money growth, ≈54% at 20%. |
| **Compliance** `specs/taxpayers.yaml` | 12 taxpayers, 4×3 lattice | social influence (Zaklan model) | tax morale, audit × penalty, tax rate | A 3-evader cluster pulls compliance down to ~70%. More audits raise the floor. |

Absolute scales (κ, β, Γ, …) are dimensionless calibration knobs, chosen by exact-evolution scans so effects sit above the Γ-driven background. The network structure and the direction each policy pushes come from the cited literature (`CITATIONS.md`).

## How we know it's right

- **Independent Hamiltonian.** `validation/reference.py` builds H from raw `(edges, h, Γ)` with NumPy alone. It agrees with the engine on Shiven's test grid, and (`tests/test_integration.py`) on every real preset to 1e-12.
- **Trotter convergence.** State infidelity falls with slope ≈ −2 for first order and ≈ −4 for second order, and Z-basis observables converge with slope ≈ −2 (`validation/figures/fig1_trotter.png`, `fig5_observable_error.png`).
- **Γ = 0 test.** All terms commute: infidelity and motion are zero to machine precision (~1e-15) on the validation grid and on every preset.
- **Presets vs exact evolution.** Every shipped spec stays within 1e-2 of exact evolution out to t_max.
- **First = second order on our observables.** For a computational-basis start and Z-basis measurements, the two orders agree to 1e-14 (finding 5). So the specs and the hardware adapter use first order, at half the two-qubit gates.
- **Memory wall.** 16·2ⁿ bytes passes a 31.6 GiB laptop at n = 31. Two-qubit gates per step grow linearly (`fig2_memory_wall.png`).
- **Classical baseline.** Glauber Monte Carlo on the same J, h and graph is a different model with a temperature. It forgets its start, while the coherent model conserves energy (`fig4_glauber.png`).

## Hardware

`python -m backends.hardware plan|fake|submit|fetch specs/banks.yaml --device …`. The bank preset transpiles to 27–115 two-qubit gates for t = 0.5–2 on FakeBoston (seeded). A noisy-simulator rehearsal is cached in `results/hardware/` and drawn in the demo, labelled as such. Real-hardware runs need your IBM token; see `README_DEMO.md`.

## Versions

Qiskit 2.6.2, qiskit-ibm-runtime 0.51.0, qiskit-aer 0.18.2, NumPy, SciPy, NetworkX, PyYAML, Matplotlib. The validation figures were made with the pins in `validation/requirements.txt`. No dependency on the archived `qiskit-finance` or the unsupported `qiskit-algorithms` / `qiskit-nature`.
