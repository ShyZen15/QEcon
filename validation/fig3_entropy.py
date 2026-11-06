"""Fig 3: entanglement entropy. With no transverse field, there is no entanglement.

Only true because we start from a definite bit-string: ZZ terms alone can entangle a
superposition. Here "entanglement" is a correlation diagnostic of the model, not a claim
about real people.
Run from the repo root:  python -m validation.fig3_entropy
"""
import math

import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

from core.engine import compile_ising, evolve
from validation import reference as ref
from validation.plotting import AQUA, BLUE, ORANGE, heading, save
from validation.systems import standard_system

T_MAX = 6.0
MAX_DT = 0.05
SCALES = ((1.0, "Full Γ", BLUE, "o"), (0.5, "Half Γ", ORANGE, "s"), (0.0, "Γ = 0", AQUA, "^"))


def main():
    times = np.linspace(0, T_MAX, 121)
    check_times = np.arange(1.0, T_MAX + 0.5, 1.0)

    fig, ax = plt.subplots(figsize=(11, 6.2))
    fig.subplots_adjust(left=0.085, right=0.84, top=0.8, bottom=0.12)
    heading(fig, "Entanglement only appears when the transverse field is on",
            "Entropy between agents 0–5 and 6–11, from a definite starting bit-string.  "
            "Lines are exact, points are the circuit.")

    data = {"times": times.tolist(), "circuit_times": check_times.tolist(), "curves": {}}
    for scale, label, color, marker in SCALES:
        system = standard_system(gamma_scale=scale)
        n = system.n
        H = compile_ising(n, system.edges, system.h, system.gamma)
        exact = [ref.half_entropy(psi, n) for psi in ref.exact_series(system, times)]
        circuit = [
            ref.half_entropy(
                Statevector(evolve(H, t, math.ceil(t / MAX_DT), system.init_ones, 2)).data, n)
            for t in check_times
        ]
        gap = max(abs(c - exact[int(np.argmin(np.abs(times - t)))]) for c, t in zip(circuit, check_times))
        assert gap < 2e-2, (label, gap)
        ax.plot(times, exact, color=color)
        ax.plot(check_times, circuit, marker, color=color, markeredgecolor="white", markersize=9, label=label)
        ax.annotate(f"{label}: {exact[-1]:.2f} bits", (T_MAX * 1.015, exact[-1]), va="center",
                    annotation_clip=False, fontsize=12.5)
        data["curves"][label] = {"gamma_scale": scale, "exact": exact, "circuit": circuit,
                                 "max_gap_circuit_vs_exact": gap}

    zero = data["curves"]["Γ = 0"]
    assert max(zero["exact"] + zero["circuit"]) < 1e-9
    assert data["curves"]["Full Γ"]["exact"][-1] > 0.5

    ax.set_xlabel("Time t (units of 1/J)")
    ax.set_ylabel("Half-system entropy (bits)")
    ax.set_xlim(0, T_MAX)
    ax.set_ylim(bottom=-0.05)
    ax.legend(loc="upper left")

    save(fig, "fig3_entropy", data)
    for curve in data["curves"].values():   # ASCII only: Windows consoles can't print Gamma
        print(f"gamma scale {curve['gamma_scale']:g}: S(t={T_MAX:g}) = {curve['exact'][-1]:.3f} bits, "
              f"circuit gap {curve['max_gap_circuit_vs_exact']:.1e}")


if __name__ == "__main__":
    main()
