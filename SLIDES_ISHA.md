# Isha's slides, deck assembly, and Q&A

## Deck order (Isha assembles)

1. Title: QEcon, a domain-to-Hamiltonian compiler for agent economies
2. What we built: the 4-stage compiler (YAML spec → `SparsePauliOp` → Trotter circuit → economic observables) *(Snigdha)*
3. Engine: the four functions, benchmark *(Snigdha)*
4. **From economics to a Hamiltonian** *(Isha, slide A)*
5. **Two presets, one compiler** *(Isha, slide B)*
6. Why quantum: the memory wall *(Shiven)*
7. How we know it's right: Trotter convergence + Γ = 0 *(Shiven)*
8. **What we do NOT claim** *(team; Isha writes it)*
9. Policy you can play with *(Arsh, slide C, see `SLIDES_ARSH.md`)*
10. Toward hardware *(Arsh, slide D)*
11. Live demo *(Arsh)*: script in `README_DEMO.md`
12. References *(Isha: from `CITATIONS.md`)*

---

## Slide A: From economics to a Hamiltonian

**Title:** Every economic knob becomes one term of one Hamiltonian

H = −Σ J_ij Z_iZ_j − Σ h_i Z_i − Σ Γ_i X_i

| Economics | Hamiltonian | Source |
|---|---|---|
| agent (bank, firm, taxpayer) | qubit: \|0⟩ solvent/hold/comply, \|1⟩ insolvent/raise/evade | |
| exposure / imitation / pricing complementarity | ZZ coupling J_ij | Elliott–Golub–Jackson 2014; Cooper & John 1988 |
| policy & fundamentals: capital buffer, bailout, money growth, VAT, audits | longitudinal field h_i | Basel III; Zaklan et al. 2009 |
| uncertainty / indecision | transverse field Γ_i, **the only non-commuting term** | quantum cognition (Pothos & Busemeyer) |

**Figure:** a 6-line YAML snippet (`fields: money_growth: 12`) with an arrow to `h_i = 0.8 − 0.1·(12 − 2)`.

**One-liner:** *The physics is generic. The economics lives in the parameters, and every parameter has a citation.*

Speaker notes (30 s): "Person 3's job was to make 'isn't this just a magnet?' have an answer. Every number in our YAML has a source comment. The bank couplings come from the Elliott–Golub–Jackson cross-holdings model, the capital fields come from Basel III, and the validator rejects a spec before anything expensive runs, for example when cross-holdings don't leave outside shareholders."

---

## Slide B: Two presets, one compiler

**Title:** Policy is a field knob: same YAML → circuit pipeline

**Left figure: `figures/banks_bailout.png`.** 8 banks, core–periphery, Core-B fails.
- No shock (Γ noise only) vs Core-B fails vs + bail out Core-A vs + ring-fence Peri-3/Peri-4
- Second figure if there's room: `figures/banks_lightcone.png` (heatmap sorted by distance from Core-B)

**Right figure: `figures/firms_money_sweep.png`.** 12 firms on a 4×3 supply grid, money growth 2 / 8 / 14 / 20 %.

**One-liners:**
- *Contagion: Core-A's peak failure probability goes from 3% (no shock) to ~47% when Core-B fails, and a bailout field cuts it to ~9%.*
- *Inflation expectations stay anchored, then de-anchor abruptly once money growth gets large: a threshold, not a straight line.*

Speaker notes (30 s): "We always compare against the no-shock baseline. The transverse field makes weak banks flicker on its own, so contagion is the *excess* over that. And a failing small bank barely touches the core, because its hub is held up by its other solvent neighbours. That's why the demo shocks a core bank."

---

## Slide: What we do NOT claim

- ❌ Better economic forecasts. This is a stylized, quantum-*like* model.
- ❌ A speedup over classical econophysics. Zaklan / Bornholdt models are classical Monte Carlo and scale to 10⁶ agents. Our coherent model is a *different* model.
- ❌ That people or economies are physically quantum. Hilbert space is used as a probability calculus.
- ❌ That inter-agent entanglement is empirically real. It's a correlation diagnostic of our model; quantum-cognition evidence is single-agent and contested (Boyer-Kassem et al. 2016).
- ❌ Estimated parameters. Network structure and policy directions are sourced; absolute scales (κ, β, Γ) are calibration knobs.
- ⚠️ Real exposure is directed. A Hermitian ZZ coupling is symmetric, so we use (A_ij + A_ji)/2.
- ⚠️ Coherent dynamics is reversible: cascades oscillate and partially un-spread. We report peaks and time-averages.

✅ **What we do claim:** a working compiler, validated against exact evolution (Trotter error < 1e-2 on every preset); circuits that scale linearly in interactions while exact simulation needs 16·2ⁿ bytes *for this coherent model*.

---

## Q&A that comes to Isha

| Q | Answer |
|---|---|
| "Isn't this just relabeling a magnet?" | "Mathematically yes, on purpose: the compiler is the contribution. The economics is in the parameters: J from the Elliott–Golub–Jackson dependency matrix, h from Basel III buffers and a money-growth rule, every number source-commented." |
| "Where do the numbers come from?" | "Structure from the literature: EGJ cross-holdings, core–periphery tiering (Craig & von Peter), a 2D supply grid. Absolute scales are dimensionless calibration knobs we chose by scanning exact evolution, and we say so." |
| "Real contagion is directed. Why symmetric?" | "A Hermitian ZZ term must be symmetric, so we average A_ij and A_ji. That loses direction, and it's on our 'do not claim' slide." |
| "Why does the cascade un-spread?" | "Coherent evolution is reversible and conserves energy. It doesn't relax to equilibrium. The shocked bank's negative field keeps it down; we read peaks and time-averages." |
| "Why did you seed a core bank, not a small one?" | "We tried both. A failing small bank barely moves its hub, because the hub's other solvent neighbours hold it up. That's a real feature of the model, not a bug." |
| "Why a grid, not a chain?" | "The 1D transverse-field Ising chain is free-fermion solvable. A 2D grid plus a longitudinal field isn't, and our validator warns if you build a chain with h = 0." |
| "Why does inflation pressure jump between 14% and 20%?" | "The ferromagnetic coupling makes anchored expectations self-reinforcing. Each firm's neighbours hold it in place until the money field beats the coupling. That's a threshold, i.e. de-anchoring." |
| "What's Γ economically?" | "The rate an agent's decision rotates between options with no pressure: uncertainty. At Γ = 0 every term commutes and nothing moves; our tests check that on every preset." |
| "Is quantum economics legit?" | "Quantum-like models are peer-reviewed but contested (Pothos & Busemeyer 2022 review; Boyer-Kassem et al. 2016 critique). We treat it as a hypothesis class to explore, not evidence." |
