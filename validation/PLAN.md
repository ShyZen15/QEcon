# Validation plan (Person 2, Shiven)

Written Thu Nov 5, 3:30pm EST. Judging is Fri Nov 6.
Every "measured" number below came from a real run of Snigdha's `core/engine.py`
(commit `ee35ff0`) on Qiskit 2.6.2, NumPy 2.5.4, SciPy 1.18.1, Python 3.13.

## Status (Thu 3:50pm)

Built: 33 tests passing, all five figures in `validation/figures/`, each with its
numbers in a JSON file. We are about two hours ahead of the 6pm gate.

The tests were themselves tested: 8 deliberate bugs were injected into scratch copies
(sign flips on J, h and Γ, reversed qubits, doubled time, wrong seed qubit, X terms
before Z terms, and the Glauber lockstep bug) and every one was caught.

Still open: Shiven's explain-back on each figure, the commit and push, and rerunning
the checks on Isha's presets when they land.

## What this workstream has to prove

The deck's spine has two slides that depend on this folder:

- **Why quantum:** the memory wall figure.
- **How we know it's right:** the Trotter convergence figure and the Γ=0 test.

Everything here answers one judge question: "How do you know your circuit computes
what you say it computes?" The answer is that we built the same physics two
independent ways and measured the gap.

## Findings that change the original plan

### 1. We are behind the schedule

The 2pm merge gate has passed. GitHub has only `master` (just "Hello, World") and
`snigdha-core-engine`. Nothing from Isha or Arsh is pushed, and the engine is not
merged to `master`. Figures are due at 6pm, so this plan is ordered by priority.

### 2. The doc's code snippet would produce a fake result

`Statevector(qc)` on a circuit that still contains a `PauliEvolutionGate` uses the
gate's `to_matrix()`, which since Qiskit 2.2 is the **exact** exponential. Trotter is
skipped without any warning.

| n=6, order 1 | r=1 infidelity | r=4 infidelity |
|---|---|---|
| `unroll=True` (real Trotter) | 8.8e-01 | 5.3e-02 |
| `unroll=False` (silently exact) | ~0 | ~0 |

It is also very slow: 17s at n=10, and it did not finish in over 4 minutes at n=12.
Snigdha's `evolve()` unrolls by default, so the engine is fine. **Never pass
`unroll=False` in this folder.** A test guards this.

### 3. `exact_state()` is not an independent check

It uses `H.to_matrix()` from the same `SparsePauliOp` the circuit uses. A sign or
qubit-order bug in `compile_ising` would be in both, and they would still agree.
So `validation/reference.py` builds H from the raw `(edges, h, gamma)` with plain
NumPy bit operations and no Qiskit.

Measured: the engine and the independent build agree to 8.9e-15. The engine is correct.

### 4. Uniform parameters hide bugs

`bench.py` and `steps_check.py` use a 1D chain with identical h and Γ on every site.
A swapped qubit order is invisible there, and a 1D chain is the case the doc warns
judges will attack. We use a 3×4 grid with a different J, h and Γ on every site.

### 5. Order 1 and order 2 give identical Z-basis results (surprise)

The doc implies second order beats first order on observables. For our setup that is
false, and it looks like a plotting bug unless we explain it.

| r | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| ⟨M⟩ error, order 1 | 7.34e-2 | 1.11e-2 | 2.94e-3 | 7.31e-4 | 1.82e-4 | 4.56e-5 |
| ⟨M⟩ error, order 2 | 7.34e-2 | 1.11e-2 | 2.94e-3 | 7.31e-4 | 1.82e-4 | 4.56e-5 |

Why: write D for all the Z and ZZ terms (they commute) and X for the transverse terms.

- Order 1, r steps: `(e^-iX e^-iD)^r`
- Order 2, r steps: `e^-iD/2 (e^-iX e^-iD)^r e^+iD/2`

The two differ only by diagonal phases at the two ends. A diagonal phase does nothing
to a computational-basis start state, and nothing to Z-basis measurement probabilities.
So every bitstring probability matches.

Measured: largest difference across all 4096 bitstrings is about 5e-15 at every r, even
though the states themselves differ (state infidelity between them is 7e-2 at r=4).
Starting from |+⟩ⁿ instead breaks the match (1.4e-3), which confirms the mechanism.

Consequences:

- ⟨M⟩, ⟨Z_iZ_j⟩ and P(failed) all converge with slope −2 for **both** orders.
- State infidelity still separates them (−2 vs −4), so Figure 1 is unaffected.
- ⟨X̄⟩ is not diagonal, so it does separate them. Add it to Figure 5.
- **Tell Arsh:** for hardware, `order=1` gives the same Z-basis numbers as `order=2`
  at half the two-qubit gates (17 vs 34 RZZ per step on the 3×4 grid). This depends
  on `compile_ising` keeping all Z terms before X terms, which a test locks in.

### 6. "Exactly zero" means machine precision

At Γ=0 the measured infidelity is about −1e-14 (yes, negative: floating-point rounding)
and the probability change is about 1e-14. Say **"zero to machine precision"** on the
slide. Negative values also break log axes, so the plot needs a labelled floor.

### 7. Glauber depends heavily on temperature

Same J, h, graph and seed, starting at ⟨M⟩ = 0.667:

| Model | Result |
|---|---|
| Glauber, T=1.0 | rises to about 0.80 (seeded agents heal) |
| Glauber, T=2.5 | decays to about 0.01 |
| Coherent, Γ~0.5 | drifts to about 0.5 with small wiggles |

So "identical parameters" can only mean identical J, h, graph and seed. Glauber has a
temperature that the coherent model lacks, and the coherent model has Γ that Glauber
lacks. Their time axes (sweeps vs 1/J) are also different units. Show two temperatures,
use separate time axes, and don't imply one is a noisy version of the other.

### 8. The doc's "oscillation" story doesn't fit our data. Energy does.

The doc says the coherent model oscillates while Glauber doesn't. On our grid the
oscillations are small: the seeded agent stays between −1.00 and −0.66 for all of t = 12.
The measured difference is energy. Coherent ⟨H⟩ is constant to 3e-14, and the seeded
agent stays near its start. Glauber has a heat bath and forgets its start within a few
sweeps. **Say "conserves energy" on stage, not "oscillates".**

### 9. My first Glauber code had a real bug (fixed)

It drew one random site and used it for all 4,000 replicas, so the whole ensemble jumped
in lockstep. No assertion noticed. It was spotted by looking at the plot (a −1 to +0.73
jump in one sweep). Fixed, with two new tests, including one that checks long-run Glauber
against the exact Boltzmann average over all 4096 states.
Lesson: passing checks don't replace looking at the figure.

### 10. The contagion heatmap needs Γ in the right range, and a baseline

Γ also flips agents with no seed at all, so raw P(failed) overstates contagion at high Γ.
Measured on the grid with one seed: the largest rise in P(failed) caused by the seed,
and the largest P(failed) with no seed anywhere.

| Mean Γ (mean J ≈ 1) | Neighbours, effect of seed | Far agent, effect of seed | No-seed background |
|---|---|---|---|
| 0.43 | +0.23 to +0.45 | 0.00 | 0.02 to 0.03 |
| 0.87 | +0.50 to +0.52 | +0.19 | 0.11 to 0.14 |
| 1.30 | +0.37 to +0.38 | +0.23 | 0.30 to 0.35 |
| 1.73 | +0.17 to +0.19 | +0.12 | 0.60 to 0.64 |

So Γ around 0.4 to 0.9 × J gives the clearest spread, and above about J the background
swamps it. The heatmap should plot P(failed | seed) − P(failed | no seed). This is from the
test grid, not Isha's real bank network, so recheck it on that preset.

## Why we use this code

| Choice | Why |
|---|---|
| `SparsePauliOp.from_sparse_list` | Terms use integer qubit indices. Qiskit label strings read right to left, which is the classic source of qubit-order bugs. |
| `PauliEvolutionGate` + `LieTrotter` / `SuzukiTrotter` | Qiskit's own Trotter synthesis. Hand-written RX/RZZ circuits commonly get the factor of 2 wrong (`exp(-itX)` is `RX(2t)`). |
| `transpile(...)` inside `evolve()` | Breaks the evolution gate into real gates. It is faster, and it is what makes the simulation real Trotter (finding 2). |
| `StatevectorEstimator` | Noiseless and shot-free, so any error we see is Trotter error and not sampling noise. |
| `expm_multiply` on a sparse H | Applies exp(−itH) to a vector without building the dense matrix. Memory is about 2ⁿ instead of 4ⁿ, which gets us to about 20 qubits. |
| NumPy-built H in `reference.py` | The only reference that shares no code with the thing being tested (finding 3). |
| 1 − \|⟨ψ_exact\|ψ_trot⟩\|² | Ignores global phase, which has no physical meaning. |
| SVD of the reshaped state for entropy | Fast, and independent of `partial_trace`. The two agree to 1e-12, so we use one as a check on the other. |
| Vectorised Glauber in NumPy | This is the classical model the econophysics papers use, so it is the honest baseline. |
| Not `qiskit-algorithms`, `qiskit-nature`, `qiskit-finance`, Aer | Unsupported, incompatible or archived per the doc, and we don't need them at n ≤ 14. |

Standard test system, shared by all five figures: 3×4 grid, 12 agents, 17 edges,
seed 7, J ∈ [0.5, 1.5], h ∈ [−0.6, 0.6], Γ ∈ [0.3, 0.7], seeded agents (0, 5), t = 1.

- Grid, because 1D chains are classically solvable and that is a judge question.
- h ≠ 0, because it breaks the free-fermion solution.
- Different values per site, because of finding 4.
- 12 agents, because it matches the engine's target and each run takes under a second.

## Files

```
validation/
  PLAN.md          this file
  validation.ipynb everything below in one notebook. The .py files stay the source of
                   truth, so a change there must be copied here too
  requirements.txt pinned versions the figures were made with
  systems.py       the standard test system, used by everything
  reference.py     NumPy-only H, exact evolution, entropy helpers
  glauber.py       the classical Monte Carlo baseline
  plotting.py      shared chart style and output helpers
  test_engine.py   the pytest gate (below)
  fig1_trotter.py  fig2_memory_wall.py  fig3_entropy.py
  fig4_glauber.py  fig5_observable_error.py
  run_all.py       regenerates every figure
  figures/         PNGs for the deck, plus the numbers behind them as JSON
```

Run from the repo root, for example `python -m validation.fig1_trotter`, so that
`core.engine` imports. We only import `compile_ising`, `evolve`, `exact_state` and
`magnetization`. Nothing here edits `core/engine.py`.

## The gate: `test_engine.py`

No figure counts until these pass. Each one is a judge question we have already answered.

| Test | Pass condition | Measured |
|---|---|---|
| Engine H equals independent H | max diff < 1e-12 | 8.9e-15 |
| One qubit matches ⟨Z⟩ = cos(2Γt) | diff < 1e-12 | ~1e-16 |
| **Γ=0: no motion, no error, any r** | < 1e-12 | ~1e-14 |
| Trotter is really running (r=1 is wrong) | infidelity > 1e-3 | 0.71 to 0.91 |
| Convergence slopes (r = 4..32) | −2 ± 0.2 and −4 ± 0.3 | −2.03, −4.07 |
| Order 1 and 2 probabilities match | < 1e-12 | ~5e-15 |
| Entropy: SVD equals `partial_trace` | < 1e-9 | ~1e-12 |
| Glauber energy equals diag(H) at Γ=0 | exact | passes |
| Glauber flip cost equals energy difference | exact | passes |
| Glauber reaches exact Boltzmann average | < 0.02 | passes |
| Glauber replicas update independently | jump below theoretical bound | passes |

## Figures, in priority order

The original list is numbered by script. This is the order we build them in, following
the deck's spine and the doc's cut order (entropy is the one that may be cut).

**Fig 1: Trotter convergence + Γ=0 (never cut).** Log-log infidelity vs r for both
orders, with reference slopes. Fit only r = 4..32, because r=1 is outside the
small-step regime and bends the line. Γ=0 is drawn at a labelled machine-precision floor.
Claim: "Error falls at the rate theory predicts, and vanishes when the transverse field
is off."

**Fig 2: Memory wall.** 16·2ⁿ bytes against n, with RZZ count from real compiled
circuits (`count_ops`, not a formula) on square grids. Bytes and gates are different
units, so use two panels with a shared n axis, not one axis. Overlay this laptop's 32 GB
(a single state vector stops fitting at n=31) and Nighthawk's vendor-stated 5,000-gate
budget. Label it "exact statevector, coherent model, per Trotter step", and note that
tensor networks can go further at low entanglement.
Claim: "Exact memory doubles per agent. Gate count grows with the number of edges."

**Fig 5: Observable error.** Max error over a time window vs r, because a single time
can hit an accidental zero crossing. Show ⟨M⟩, ⟨ZZ⟩ and ⟨X̄⟩. Reuses Fig 1's machinery.
Annotate the order 1 and 2 overlap so nobody reads it as a bug (finding 5).
Measured slopes: ⟨M⟩ −1.97 and ⟨ZZ⟩ −2.05 for both orders. ⟨X̄⟩ −0.85 and −2.08, which is
where the textbook first and second order rates actually show up.
Claim: "For the numbers the app reports, 16 steps gives under 6e-4 error on ⟨M⟩ (worst
case up to t = 2), and first order is enough."

**Fig 4: Glauber vs coherent.** Two panels with their own time axes, two temperatures,
plus one single-agent trace (findings 7 and 8).
Claim: "These are different models: one conserves energy, the other relaxes to a
temperature-set equilibrium."

**Fig 3: Entropy (cut first if late).** Half-system entropy S(t), Γ=0 vs Γ>0.
Measured: 0 at Γ=0, and 0.001 → 0.03 → 0.11 → 0.44 → 0.95 bits at t = 0.25, 0.5, 1, 2, 4,
reaching 1.22 bits at t = 6. Half Γ reaches only 0.12 bits.
Say which cut we used, and that it only applies to basis-state starts (ZZ alone can
entangle a superposition). Claim: "No transverse field, no entanglement."

## Judge questions on each figure

**Fig 1.** "Why is Γ=0 not exactly zero?" Rounding in 64-bit floats. Its worst value is
6e-15, over seven orders of magnitude below the smallest Trotter error on the plot (2e-7).
"Why fit only from r=4?" At r=1 and 2 the steps are too large for the small-step formula
to apply. Fitting all points gives −1.98 and −4.33, so the conclusion doesn't depend on it.

**Fig 2.** "Doesn't this prove quantum advantage?" No. It compares exact state vectors to
circuit size for our own model. Tensor networks reproduced IBM's 127-qubit experiment, and
hardware noise limits depth. "Are those gate counts real?" They are counted from compiled
circuits, before routing. The 5,000 figure is IBM's own number.

**Fig 5.** "Why do the lines overlap, is that a bug?" No: the two orders differ only by
diagonal phases at the ends, which can't change Z-basis probabilities. The ⟨X⟩ panel shows
they are different circuits. A test enforces this.

**Fig 4.** "Which model is right?" We make no claim about real economies. Glauber is the
published classical model, ours is a different hypothesis. "Why two temperatures?" Glauber's
result depends strongly on T, so one value would be cherry-picking.

**Fig 3.** "What does entanglement mean for a bank?" It's a correlation measure inside the
model, not a claim about real agents. "Is Γ=0 always zero?" Only from a definite bit-string.
ZZ terms alone can entangle a superposition.

## Schedule (original targets; all built by 3:50pm)

| Target | Work | Who |
|---|---|---|
| 3:45 | Set up `.venv` and `requirements.txt`, write `systems.py`, `reference.py` | Claude |
| 4:05 | `test_engine.py` green | Claude writes, Shiven runs |
| 4:30 | **Fig 1 done. If only one thing ships, it's this.** | both |
| 4:50 | Fig 2 | both |
| 5:05 | Fig 5 | both |
| 5:35 | Fig 4 | both |
| 5:55 | Fig 3 | both |
| 6:00 | **Gate:** figures pushed, tell the team | Shiven |
| 6 to 8 | Rerun the checks on Isha's real presets once they land | both |
| 8:00 | Freeze | |
| 9 to 11 | Two slides, rehearsal | Shiven |

If a slot slips by 15 minutes or more, cut Fig 3, then simplify Fig 4 to one temperature.
Fig 1, the Γ=0 test and Fig 2 are not cuttable.

## How we work together

For each figure:

1. Claude writes the script and runs it.
2. The script asserts its own pass conditions, so a wrong result fails loudly.
3. Claude shows you the figure and the numbers.
4. **You explain it back in one sentence, and try one judge question on it.** On stage
   you answer for this code, so this step is not optional.
5. You approve, then we commit to `shiven-validation`. Pushes happen only when you say so.

Rules:

- Only touch `validation/`. An engine bug goes to Snigdha with a failing test.
- A number on a slide must come from a JSON file in `figures/`, never from memory.
- If a result surprises us, stop and find out why before plotting it. Finding 5 came
  from exactly that.

## Messages to send the team

**Snigdha:**
- Please merge `snigdha-core-engine` to `master`, and tell me your Qiskit version.
- The contract says `observables(n) → dict` and `run(circuits, obs, backend) → array`.
  The engine has `Plugin.observables` returning a list, and `run_time_series` returning
  a list of arrays. Isha and Arsh need to know which one is final.
- Good news: the engine passes an independent check, and the target is met (12 agents,
  10 time points, 0.34s against the 5s goal).
- Please keep `unroll=True` as the default (finding 2).

**Isha:** Push the bank and firm presets as soon as they build, even if rough. I'll run
the checks on the real parameters. Keep Γ around 0.4 to 0.9 × J on the bank preset: above
about J, agents flip on their own and the contagion signal gets buried.

**Arsh:** Did the hardware jobs go in? Use `order=1`: same Z-basis numbers, half the
two-qubit gates. Never use `unroll=False` when simulating. For the light-cone heatmap, plot
P(failed | seed) − P(failed | no seed), so background flipping isn't shown as contagion.

**Everyone:** Figures land as PNGs in `validation/figures/` on `shiven-validation`.
Tell me if the deck needs a specific size.

## Still unknown

- Whether Isha and Arsh have unpushed work.
- Whether Arsh's hardware jobs were submitted (the 9am gate).
- What Qiskit version the rest of the team has. There is no `requirements.txt` yet.
- Fig 4 story beyond the sanity run. It needs a look once plotted.
- Nighthawk's 5,000-gate figure and other hardware numbers are vendor-reported, not
  checked by us. Label them that way.
