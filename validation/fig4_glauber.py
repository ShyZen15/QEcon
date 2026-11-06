"""Fig 4: the classical Glauber model and our coherent model are different models.

Shared: J, h, graph, seeded agents. Glauber adds a temperature, the coherent model adds
Gamma, and their clocks are different units, so each gets its own time axis.

The core difference is energy. Unitary evolution conserves <H> and has no bath to absorb
energy, and here the seeded agent stays near where it started. Glauber is coupled to a
heat bath, so it forgets the start and settles at a temperature-set equilibrium.
Run from the repo root:  python -m validation.fig4_glauber
"""
import math

import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

from core.engine import compile_ising, evolve
from validation import glauber, reference as ref
from validation.plotting import BLUE, ORANGE, heading, save
from validation.systems import standard_system

T_MAX = 12.0
SWEEPS = 40
TEMPERATURES = (1.0, 2.5)
SEEDED_AGENT = 0
MAX_DT = 0.05


def main():
    system = standard_system()
    n = system.n
    H = compile_ising(n, system.edges, system.h, system.gamma)
    H_matrix = ref.hamiltonian(n, system.edges, system.h, system.gamma)

    times = np.linspace(0, T_MAX, 241)
    states = ref.exact_series(system, times)
    z = np.array([ref.z_expectations(psi, n) for psi in states])
    coherent_M, coherent_agent = z.mean(axis=1), z[:, SEEDED_AGENT]
    energy = np.array([np.real(np.vdot(psi, H_matrix @ psi)) for psi in states])
    energy_drift = float(np.abs(energy - energy[0]).max())
    assert energy_drift < 1e-9, energy_drift

    check_times = np.arange(1.0, T_MAX + 0.5, 1.0)
    circuit_z = []
    for t in check_times:
        psi = Statevector(evolve(H, t, math.ceil(t / MAX_DT), system.init_ones, 2)).data
        circuit_z.append(ref.z_expectations(psi, n))
    circuit_z = np.array(circuit_z)
    circuit_gap = float(np.abs(
        circuit_z - np.array([ref.z_expectations(p, n) for p in ref.exact_series(system, check_times)])
    ).max())
    assert circuit_gap < 2e-2, circuit_gap

    runs = {T: glauber.run(system, T, SWEEPS) for T in TEMPERATURES}
    sweeps = np.arange(SWEEPS + 1)

    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.78, bottom=0.13, wspace=0.07)
    heading(fig, "Same economy, different models: one conserves energy, one relaxes",
            "Shared: J, h, graph, seeded agents. Coherent adds Γ, Glauber adds temperature T. "
            "Time axes are different units and are not comparable.")

    left.plot(times, coherent_M, color=BLUE, label="All agents")
    left.plot(times, coherent_agent, color=ORANGE, label=f"Seeded agent {SEEDED_AGENT}")
    left.plot(check_times, circuit_z.mean(axis=1), "o", color=BLUE, markeredgecolor="white", label="Circuit points")
    left.plot(check_times, circuit_z[:, SEEDED_AGENT], "o", color=ORANGE, markeredgecolor="white")
    left.set_title("Coherent model: seeded agent stays near its start")
    left.set_xlabel("Time t (units of 1/J)")
    left.set_ylabel("⟨Z⟩  (+1 = |0⟩, −1 = |1⟩)")
    left.set_ylim(-1.08, 1.08)
    left.legend(loc="center right", bbox_to_anchor=(1.0, 0.45))

    for T, style in zip(TEMPERATURES, ("-", (0, (4, 2)))):
        right.plot(sweeps, runs[T].mean(axis=1), color=BLUE, linestyle=style, label=f"All agents, T = {T:g}")
        right.plot(sweeps, runs[T][:, SEEDED_AGENT], color=ORANGE, linestyle=style, label=f"Seeded agent, T = {T:g}")
    right.set_title("Glauber Monte Carlo: start is forgotten")
    right.set_xlabel("Monte Carlo sweeps (4,000 replicas)")
    right.legend(loc="lower right")

    data = {
        "max_abs_gap_circuit_vs_exact": circuit_gap,
        "coherent_energy_start": float(energy[0]),
        "coherent_energy_max_drift": energy_drift,
        "coherent_seeded_agent_z_final": float(coherent_agent[-1]),
        "coherent_seeded_agent_z_max": float(coherent_agent.max()),
        "coherent_average_z_range": [float(coherent_M.min()), float(coherent_M.max())],
        "glauber": {
            str(T): {
                "final_average": float(runs[T][-1].mean()),
                "final_seeded_agent": float(runs[T][-1][SEEDED_AGENT]),
            }
            for T in TEMPERATURES
        },
    }
    save(fig, "fig4_glauber", data)
    print(data)


if __name__ == "__main__":
    main()
