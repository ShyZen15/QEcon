"""Fig 2: the memory wall. This is the deck's "why quantum" picture.

Gate counts come from real compiled circuits, not a formula. Memory is checked
against an actual state vector before being extrapolated.
Run from the repo root:  python -m validation.fig2_memory_wall
"""
import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

from core.engine import compile_ising, evolve
from validation.plotting import AQUA, BLUE, INK_SECONDARY, ORANGE, heading, save
from validation.systems import grid_edges

GIB = 2 ** 30
LAPTOP_GIB = 31.6              # this machine's physical RAM
NIGHTHAWK_GATES = 5000         # IBM-stated two-qubit gate budget (vendor figure)
CZ_PER_RZZ = 2                 # Nighthawk is CZ-native, and an RZZ costs 2 CZ
GRIDS = [(2, 2), (3, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (10, 12)]
STEP_COUNTS = (1, 4, 8)


def statevector_bytes(n):
    return 16 * 2.0 ** n


def rzz_per_step(rows, cols):
    """Two-qubit gates in one first-order step, counted from the compiled circuit."""
    n = rows * cols
    edges = {pair: 1.0 for pair in grid_edges(rows, cols)}
    H = compile_ising(n, edges, [0.1] * n, [0.5] * n)
    circuit = evolve(H, 1.0, 1, order=1)
    count = circuit.count_ops().get("rzz", 0)
    assert count == len(edges), (count, len(edges))
    return count


def main():
    for n in (10, 14):
        measured = Statevector.from_int(0, 2 ** n).data.nbytes
        assert measured == statevector_bytes(n), (n, measured)

    sizes = [r * c for r, c in GRIDS]
    rzz = [rzz_per_step(r, c) for r, c in GRIDS]
    cz = np.array(rzz) * CZ_PER_RZZ

    ns = np.arange(2, sizes[-1] + 1)
    wall = int(ns[statevector_bytes(ns) > LAPTOP_GIB * GIB][0])
    assert wall == 31, wall

    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 6.2), sharex=True)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.76, bottom=0.12, wspace=0.24)
    heading(fig, "Exact simulation memory doubles per agent. Circuit size grows with edges.",
            "Applies to exact state-vector simulation of our coherent model on square grids. "
            "Not a claim about all classical methods:\n"
            "tensor networks can go further when entanglement stays low.")

    left.plot(ns, statevector_bytes(ns), color=BLUE)
    left.axhline(LAPTOP_GIB * GIB, color=INK_SECONDARY, linestyle=(0, (4, 3)), linewidth=1.2)
    left.plot([wall], [statevector_bytes(wall)], "o", color=BLUE, markeredgecolor="white", markersize=9)
    left.set_yscale("log")
    left.set_yticks([10.0 ** p for p in range(3, 40, 6)])
    left.set_ylabel("Bytes")
    left.set_title("Memory for one exact state vector (16 · 2ⁿ bytes)")
    left.set_xlabel("Agents n")
    left.annotate(f"This laptop ({LAPTOP_GIB:g} GiB)\nruns out at n = {wall}",
                  (wall, LAPTOP_GIB * GIB), xytext=(46, 3e4), fontsize=12.5,
                  arrowprops={"arrowstyle": "-", "color": INK_SECONDARY, "linewidth": 0.8})
    left.text(sizes[-1] - 8, statevector_bytes(sizes[-1]),
              f"n = {sizes[-1]}: about 2 × 10³⁷ bytes", ha="right", va="center", fontsize=12.5)

    for steps, color, marker in zip(STEP_COUNTS, (BLUE, ORANGE, AQUA), "os^"):
        label = f"{steps} step" + ("" if steps == 1 else "s")
        right.plot(sizes, cz * steps, "-" + marker, color=color, label=label)
    right.axhline(NIGHTHAWK_GATES, color=INK_SECONDARY, linestyle=(0, (4, 3)), linewidth=1.2)
    right.text(2, NIGHTHAWK_GATES + 90, "IBM Nighthawk budget: 5,000 (vendor figure)", va="bottom", fontsize=12.5)
    right.set_ylim(0, 5800)
    right.set_title("Two-qubit gates, first order, before routing")
    right.set_xlabel("Agents n")
    right.set_ylabel("CZ count (2 per compiled RZZ)")
    right.legend(loc="upper left", bbox_to_anchor=(0.0, 0.85))

    save(fig, "fig2_memory_wall", {
        "grid_shapes": GRIDS,
        "agents": sizes,
        "rzz_per_first_order_step_measured": rzz,
        "cz_per_first_order_step": cz.tolist(),
        "laptop_gib": LAPTOP_GIB,
        "first_n_exceeding_laptop": wall,
        "bytes_at_largest_n": statevector_bytes(sizes[-1]),
        "max_first_order_steps_in_nighthawk_budget_at_largest_n": int(NIGHTHAWK_GATES // cz[-1]),
    })
    print(f"wall n={wall}; n={sizes[-1]}: {rzz[-1]} RZZ/step, {cz[-1]} CZ/step, "
          f"{NIGHTHAWK_GATES // cz[-1]} steps fit the budget")


if __name__ == "__main__":
    main()
