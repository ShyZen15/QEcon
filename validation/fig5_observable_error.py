"""Fig 5: error in the numbers the app actually reports.

Uses the worst error across several times, because a single time can land on an
accidental zero crossing and flatter the result. First and second order overlap
exactly on Z-basis observables: see finding 5 in PLAN.md. <X> is off-diagonal, so it
is included to show the two orders are genuinely different circuits.
Run from the repo root:  python -m validation.fig5_observable_error
"""
import matplotlib.pyplot as plt
from qiskit.quantum_info import Statevector

from core.engine import compile_ising, evolve
from validation import reference as ref
from validation.plotting import BLUE, ORANGE, heading, save
from validation.systems import FIT_FROM, standard_system

TIMES = (0.5, 1.0, 1.5, 2.0)
STEPS = (1, 2, 4, 8, 16, 32, 64, 128)
PAIR = (0, 1)   # a coupled pair that includes a seeded agent


def observables(psi, n):
    return {
        "M": ref.magnetization(psi, n),
        "ZZ": ref.zz_expectation(psi, n, *PAIR),
        "X": ref.x_bar(psi, n),
    }


def worst_errors(system, H, exact, order):
    """{observable: [worst error over TIMES, one per step count]}."""
    errors = {name: [] for name in ("M", "ZZ", "X")}
    for r in STEPS:
        worst = dict.fromkeys(errors, 0.0)
        for t in TIMES:
            psi = Statevector(evolve(H, t, r, system.init_ones, order)).data
            got = observables(psi, system.n)
            for name in errors:
                worst[name] = max(worst[name], abs(got[name] - exact[t][name]))
        for name in errors:
            errors[name].append(worst[name])
    return errors


def main():
    system = standard_system()
    H = compile_ising(system.n, system.edges, system.h, system.gamma)
    exact = {t: observables(ref.exact_evolve(system, t), system.n) for t in TIMES}
    first = worst_errors(system, H, exact, 1)
    second = worst_errors(system, H, exact, 2)

    for name in ("M", "ZZ"):
        gap = max(abs(a - b) for a, b in zip(first[name], second[name]))
        assert gap < 1e-11, (name, gap)
        assert abs(ref.slope(STEPS, first[name], FIT_FROM) + 2) < 0.2, name

    slopes = {
        name: {"first": ref.slope(STEPS, first[name], FIT_FROM),
               "second": ref.slope(STEPS, second[name], FIT_FROM)}
        for name in first
    }

    panels = (("M", "Average ⟨Z⟩  (Z-basis)"),
              ("ZZ", f"Pair ⟨Z{PAIR[0]}Z{PAIR[1]}⟩  (Z-basis)"),
              ("X", "Average ⟨X⟩  (not Z-basis)"))
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.8), sharey=True, sharex=True)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.78, bottom=0.13, wspace=0.08)
    heading(fig, "On Z-basis numbers, first order matches second at half the gates",
            f"Worst error over t = {', '.join(f'{t:g}' for t in TIMES)}.  12 agents, 3×4 grid.  "
            "The overlap is exact, not a plotting error: the orders differ only by diagonal phases.")

    for ax, (name, title) in zip(axes, panels):
        ax.plot(STEPS, first[name], "-o", color=BLUE, label="First order")
        ax.plot(STEPS, second[name], linestyle=(0, (3, 3)), marker="s", markerfacecolor="none",
                markeredgewidth=1.6, color=ORANGE, label="Second order")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks(STEPS, [str(r) for r in STEPS])
        ax.set_title(title, fontsize=12.5)
        ax.set_xlabel("Trotter steps r")
    axes[0].set_ylabel("Worst absolute error")
    axes[0].legend(loc="lower left")
    for ax, name in zip(axes, ("M", "ZZ")):
        ax.text(0.97, 0.93, f"both orders: slope −{abs(slopes[name]['first']):.2f}",
                transform=ax.transAxes, ha="right", fontsize=12.5)
    axes[2].text(0.97, 0.93, f"first order: slope −{abs(slopes['X']['first']):.2f}\n"
                             f"second order: slope −{abs(slopes['X']['second']):.2f}",
                 transform=axes[2].transAxes, ha="right", va="center", fontsize=12.5)

    save(fig, "fig5_observable_error", {
        "times": list(TIMES),
        "steps": list(STEPS),
        "worst_error_first_order": first,
        "worst_error_second_order": second,
        "slopes_from_r4": slopes,
    })
    for name in first:
        print(name, "r=16 err", f"{first[name][4]:.2e}", "slopes", {k: round(v, 2) for k, v in slopes[name].items()},
              "first", [f"{v:.1e}" for v in first[name]], "second", [f"{v:.1e}" for v in second[name]])


if __name__ == "__main__":
    main()
