"""The standard test system every validation script shares.

Why this system and not the chain in bench.py:
  * 2D grid: a 1D nearest-neighbour chain is classically solvable.
  * h != 0: breaks the free-fermion solution.
  * Different J, h, Gamma on every site: uniform values hide qubit-order bugs.
"""
from dataclasses import dataclass

import numpy as np

SEED = 7
ROWS, COLS = 3, 4
INIT_ONES = (0, 5)   # agents that start in |1> (failed / evading / raising)
T_REF = 1.0          # evolution time used for the convergence figures
STEPS = (1, 2, 4, 8, 16, 32)
FIT_FROM = 4         # slopes fit r >= 4 only; r = 1, 2 are outside the small-step regime


@dataclass(frozen=True)
class System:
    n: int
    edges: dict
    h: np.ndarray
    gamma: np.ndarray
    init_ones: tuple


def grid_edges(rows, cols):
    """Nearest-neighbour edges of a rows x cols grid, as (i, j) index pairs."""
    pairs = []
    for a in range(rows):
        for b in range(cols):
            q = a * cols + b
            if b + 1 < cols:
                pairs.append((q, q + 1))
            if a + 1 < rows:
                pairs.append((q, q + cols))
    return pairs


def standard_system(gamma_scale=1.0, seed=SEED, rows=ROWS, cols=COLS, init_ones=INIT_ONES):
    """3x4 heterogeneous grid. gamma_scale=0 gives the same system with Gamma off."""
    rng = np.random.default_rng(seed)
    n = rows * cols
    edges = {pair: float(rng.uniform(0.5, 1.5)) for pair in grid_edges(rows, cols)}
    h = rng.uniform(-0.6, 0.6, n)
    gamma = rng.uniform(0.3, 0.7, n) * gamma_scale
    return System(n, edges, h, gamma, tuple(init_ones))
