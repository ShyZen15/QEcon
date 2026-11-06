# Plugins & DSL (Person 3, Isha)

Domain spec (YAML) → validator → plugin → `core.engine` (Snigdha's, unchanged) → economic observables.

```
specs/banks.yaml ─▶ qecon.spec.validate ─▶ plugins.BanksPlugin.build_system() ─▶ (n, edges, h, gamma)
                                                     │
                       core.engine: compile_ising ─▶ evolve (Trotter) ─▶ StatevectorEstimator
                                                     │
                     plugin.interpret ─▶ fraction_failed(t), P(insolvent) per bank ─▶ JSON + PNG
```

## Run it (from the repo root)

```bash
pip install -r validation/requirements.txt pyyaml networkx     # or: qiskit==2.6.2 numpy scipy matplotlib pyyaml networkx pytest
python -m qecon list
python -m qecon validate specs/banks.yaml
python -m qecon run specs/banks.yaml                      # -> out/banks_core_periphery_8.json + .png
python -m qecon run specs/banks.yaml --exact --baseline   # + exact overlay, + no-shock baseline
python -m qecon run specs/banks.yaml --set "fields.bailout.nodes=[0]" --name bailout
python -m qecon run specs/firms.yaml --set fields.money_growth=20
python -m qecon.figures                                   # all slide figures -> figures/, results/ (~3 min)
python -m pytest tests -q                                 # 27 tests
```

## Presets

| Preset | Qubit | \|0⟩ / \|1⟩ | J (ZZ) | h (Z field) | Γ (X field) | Headline |
|---|---|---|---|---|---|---|
| `banks` | bank | solvent / insolvent | symmetrized EGJ dependency A = Ĉ(I−C)⁻¹ | κ·(CET1 − 7%), shock = −2 on seed, bailout = +2 | rollover uncertainty | `fraction_failed` |
| `firms` | firm on 4×3 grid | hold / raise price | strategic complementarity | anchor·credibility − β(money growth − target) − τ·ΔVAT + disorder | pricing uncertainty | `inflation_pressure` |
| `taxpayers` | taxpayer on 4×3 grid | comply / evade | social influence | morale + p·k − burden·(tax − ref) | ambivalence | `compliance_rate` |

Sign convention everywhere: **h > 0 pushes toward |0⟩** (the good state). Every number in a YAML has a source comment, or is labelled a *calibration knob*.

## For Arsh (Streamlit)

```python
from qecon.api import run_spec
from qecon.spec import load_spec, SpecError

spec = load_spec("specs/firms.yaml")
spec["fields"]["money_growth"] = slider_value          # sliders just mutate the dict
try:
    r = run_spec(spec)                                  # or run_spec(spec, overrides=["fields.money_growth=12"])
except SpecError as e:
    st.error(str(e))                                    # lists every problem
```

Slider keys: `fields.money_growth` (firms), `fields.vat_change` (firms), `fields.bailout.nodes` (banks, e.g. `[0]`), `fields.shock.nodes` (banks), `uncertainty.gamma` (all), `fields.audit_prob` (taxpayers).

**Speed:** banks (8 agents) ≈ 7 s and firms (12 agents) ≈ 15 s with the default 25 time points × 16 Trotter steps. For a snappier slider use `overrides=["simulation.n_times=13"]`. Precomputed runs are in `results/*.json`, so the app can load those instantly and only re-run on demand.

### Result shape (`results/*.json`)

```
preset, name, headline, headline_label, states {"0": "solvent", "1": "insolvent"}
times                       [T]
labels                      [n]
series[headline]            [T]   e.g. fraction_failed
series.magnetization        [T]
series.synchronization      [T]   mean <Z_i Z_j> over edges
per_agent.p_one             [T][n] P(agent in |1>)  -> heatmap / node colours
graph.edges                 [[i, j, J], ...]
graph.h, graph.gamma        [n]
graph.positions             {"0": [x, y], ...}   (spring layout for banks, grid coords for firms)
graph.distance_from_seed    [n]   hops from the seeded agent -> sort heatmap rows by this
summary                     n, edges, statevector_bytes, rzz_per_step, cx_per_step
exact (if --exact)          same series/per_agent from sparse expm;  trotter_max_error
baseline/excess (if --baseline)  same model with the shock removed, and shocked - baseline
spec, sources, warnings, runtime_s
```

## For Shiven

`specs/banks.yaml` is the real bank network for rechecking Trotter error / Γ = 0 on a non-grid graph:
```python
from qecon.api import prepare
plugin, spec, _ = prepare("specs/banks.yaml")
n, edges, h, gamma = plugin.system()          # feed straight into compile_ising
init_ones = plugin.init_ones()                # (1,)  Core-B starts failed
```

## Validator

Collects **every** error before anything expensive runs, e.g.
```
SpecError: 3 problems in specs/banks.yaml
  - network.holdings[17]: index out of range (n = 8)
  - initial.ones: 1 listed twice
  - simulation.order: must be 1 (Lie-Trotter) or 2 (Suzuki-Trotter), got 3
```
Errors: unknown preset, wrong types/NaN, wrong lengths, indices out of range, self-holdings, duplicate pairs, cross-holding column sums ≥ 1 (EGJ needs I − C invertible), Γ < 0, bad order/backend, n > 24 (statevector memory 16·2ⁿ bytes).
Warnings: Γ = 0 (nothing moves), disconnected graph, 1D chain with h = 0 (free-fermion solvable), n > 16 (slow demo).

## Findings from calibration (worth knowing on stage)

- **Γ alone makes weakly-capitalized leaf banks flicker** (~30–40% peak P(insolvent)) with no shock at all. That's why `--baseline` exists: contagion = shocked − baseline.
- **A failing *periphery* bank barely moves the core.** Its hub is held up by its other solvent neighbours. Coherent dynamics conserves energy, and flipping a well-connected node costs ~2J per solvent neighbour. So the demo seeds a *core* bank: Core-A's peak P(insolvent) goes from 3% (no shock) to ~47%, and bailing out Core-A cuts it to ~9%.
- **Firms show a threshold.** Expectations stay anchored for moderate money growth, then de-anchor sharply (μ = 2% → ~5% peak inflation pressure, μ = 12% → ~17%, μ = 20% → ~54% at Γ = 0.8). The response is not monotone beyond ~20% (energy-resonance effect of coherent dynamics), so the sweep stops at 20.
- Calibration knobs (κ, β, τ, Γ, shock/bailout strengths) were chosen by exact-evolution scans so effects sit above the Γ noise. They are not estimated from data, and we say so.
