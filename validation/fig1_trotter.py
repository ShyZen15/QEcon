"""Fig 1: Trotter convergence and the Gamma = 0 test. Never cut this one.

Each point compares a real gate-level circuit against the independent NumPy reference.
Run from the repo root:  python -m validation.fig1_trotter
"""
import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

from core.engine import compile_ising, evolve
from validation import reference as ref
from validation.plotting import AQUA, BLUE, INK_SECONDARY, ORANGE, heading, save
from validation.systems import FIT_FROM, STEPS, T_REF, standard_system

FLOOR = 1e-16   # log axes cannot show 0 or the tiny negatives rounding produces


def infidelities(system, order):
    H = compile_ising(system.n, system.edges, system.h, system.gamma)
    exact = ref.exact_evolve(system, T_REF)
    return [
        float(ref.infidelity(Statevector(evolve(H, T_REF, r, system.init_ones, order)).data, exact))
        for r in STEPS
    ]


def reference_line(ax, value_at_last, power, label=None):
    """Theory slope, drawn just above the data so the two can be compared by eye."""
    r = np.array([STEPS[2], STEPS[-1]], dtype=float)
    ax.plot(r, 6 * value_at_last * (r / r[-1]) ** power, color=INK_SECONDARY,
            linestyle=(0, (4, 3)), linewidth=1.4, zorder=1, label=label)


def main():
    system = standard_system()
    classical = standard_system(gamma_scale=0.0)
    first = infidelities(system, 1)
    second = infidelities(system, 2)
    zero = infidelities(classical, 2)
    zero_first = infidelities(classical, 1)

    slope_first = ref.slope(STEPS, first, FIT_FROM)
    slope_second = ref.slope(STEPS, second, FIT_FROM)
    worst_zero = max(abs(v) for v in zero + zero_first)

    assert abs(slope_first + 2) < 0.2, slope_first
    assert abs(slope_second + 4) < 0.3, slope_second
    assert worst_zero < 1e-12, worst_zero

    fig, ax = plt.subplots(figsize=(11, 6.2))
    fig.subplots_adjust(left=0.09, right=0.80, top=0.82, bottom=0.12)
    heading(fig, "Trotter error falls as theory predicts, and vanishes when Γ = 0",
            f"{system.n} agents on a 3×4 grid, {len(system.edges)} edges, different J, h, Γ per site, t = {T_REF:g}."
            "  Circuit vs independent NumPy reference.")

    ax.plot(STEPS, first, "-o", color=BLUE, label="First order")
    ax.plot(STEPS, second, "-s", color=ORANGE, label="Second order")
    shown_zero = np.maximum(np.abs(zero), FLOOR)
    ax.plot(STEPS, shown_zero, "-^", color=AQUA, label="Γ = 0 (second order)")
    reference_line(ax, first[-1], -2, "Theory slopes (shifted up)")
    reference_line(ax, second[-1], -4)

    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_ylim(FLOOR / 3, 3)
    ax.set_xticks(STEPS, [str(r) for r in STEPS])
    ax.set_yticks([10.0 ** p for p in range(-16, 1, 4)])
    ax.set_xlabel("Trotter steps r")
    ax.set_ylabel("Infidelity  1 − |⟨ψ_exact|ψ_circuit⟩|²")
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.42))

    edge = STEPS[-1] * 1.12
    ax.annotate(f"slope −{abs(slope_first):.2f}\n(theory −2)", (edge, first[-1]), va="center",
                annotation_clip=False, fontsize=12.5)
    ax.annotate(f"slope −{abs(slope_second):.2f}\n(theory −4)", (edge, second[-1]), va="center",
                annotation_clip=False, fontsize=12.5)
    ax.annotate(f"zero to machine\nprecision\n(worst {worst_zero:.0e})", (edge, shown_zero[-1]),
                va="center", annotation_clip=False, fontsize=12.5)

    save(fig, "fig1_trotter", {
        "steps": list(STEPS),
        "infidelity_first_order": first,
        "infidelity_second_order": second,
        "infidelity_gamma_zero_first_order": zero_first,
        "infidelity_gamma_zero_second_order": zero,
        "slope_first_order": slope_first,
        "slope_second_order": slope_second,
        "fit_uses_steps_from": FIT_FROM,
        "worst_abs_gamma_zero_infidelity": worst_zero,
    })
    print(f"slopes {slope_first:.3f} {slope_second:.3f}  worst Gamma=0 {worst_zero:.2e}")


if __name__ == "__main__":
    main()
