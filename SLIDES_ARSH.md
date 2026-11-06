# Arsh's slides (Person 4: demo & hardware)

## Slide C: Policy you can play with

**Title:** Move a policy lever, watch the network respond

**Figure:** screenshot of the demo: Contagion with the Core-A bailout (headline + light-cone pair), or Inflation at 20% money growth.

- Levers edit the YAML spec → validator → compile → simulate in ~0.3–0.7 s
- Network colour = P(raise price / insolvent) per agent, animated over time
- Every run is shown against a counterfactual (no shock, no bailout, money on target)

**One-liner:** *A judge can move the money-supply slider and watch expectations de-anchor in real time.*

Speaker notes (30 s): "This is the same compiler pipeline, wrapped in a UI. Each slider is one field in the spec, so one term in the Hamiltonian. It runs on the simulator, so it can't fail on stage, and we always show a counterfactual so you see the policy effect, not just a curve."

## Slide D: Toward hardware

**Title:** The same circuits, transpiled for an IBM device

**Figure:** banks curve with the device diamonds (`results/hardware/*.json`). If no real-hardware run exists, use the FakeBoston rehearsal and label it **"noisy simulator, not hardware."**

| | 8-bank model |
|---|---|
| qubits | 8 |
| 2-qubit gates (t = 0.5 → 2.0) | 27 → 115 |
| 2-qubit depth | 18 → 90 |
| noise-model result vs ideal | within 0.01 |

**One-liner:** *Shallow dynamics of an 8-bank network fit today's hardware; deeper evolution degrades as e^(−gates × error), which is why we report gate counts, not promises.*

Speaker notes (30 s): "We transpile with optimisation level 3 for the device's native gates and report the two-qubit depth. Our 12-firm grid needs 300+ two-qubit gates for t = 2, so we only send the 8-bank model to hardware. We also store the noiseless result of the same shallow circuit, so we can separate device noise from Trotter error."

## Q&A that comes to Arsh

| Q | Answer |
|---|---|
| "Is the demo running on a quantum computer?" | "No, on a statevector simulator, on purpose, so it can't fail live. The yellow diamonds are the device / noise-model runs, cached from earlier." |
| "Can it run on real hardware?" | "Yes at shallow depth: 8 banks, ≤ 115 two-qubit gates for t ≤ 2 (first order: for our Z-basis observables it equals second order at half the gates, Shiven's finding 5). Signal decays like e^(−N·ε); at ε ≈ 3e-3 we keep about 70%. Here's the plan output with the transpiled gate counts." |
| "How fast is it?" | "About half a second per lever move, including the exact reference and the counterfactual. We simulate the identical Trotter circuits block by block instead of rebuilding from t = 0 each time. A test checks it matches the one-circuit-per-time engine to 1e-10." |
| "What happens at Γ = 0?" | "Drag it to zero: every term commutes, the curve goes flat, and the app tells you why." |
| "Why does the bailout only help partly?" | "It pins one bank with a strong field. Contagion can still route through the rest of the network, which the light-cone heatmap shows row by row." |
