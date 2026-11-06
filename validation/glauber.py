"""Classical Glauber Monte Carlo of the Gamma = 0 energy function.

This is the kind of model the econophysics papers run (Zaklan's taxpayers, for
example): one definite bit-string per replica, with spins flipped at random.
Spin convention matches the Hamiltonian: s = +1 is |0>, s = -1 is |1>.
"""
import numpy as np


def coupling_matrix(n, edges):
    J = np.zeros((n, n))
    for (i, j), value in edges.items():
        J[i, j] = J[j, i] = value
    return J


def energy(s, J, h):
    """-sum_{i<j} J s_i s_j - sum h s_i for rows of spins s."""
    return -0.5 * np.einsum("ri,ij,rj->r", s, J, s) - s @ h


def flip_cost(s, sites, J, h):
    """Energy change from flipping one spin per replica. `sites` is an int or one per row."""
    rows = np.arange(len(s))
    sites = np.broadcast_to(sites, rows.shape)
    return 2.0 * s[rows, sites] * (np.einsum("ri,ri->r", s, J[sites]) + h[sites])


def run(system, temperature, sweeps, replicas=4000, seed=0):
    """Returns per-agent <s_i> after each sweep, shape (sweeps + 1, n).

    One sweep is n single-spin update attempts per replica. Each replica picks its own
    site: sharing one site across replicas makes the whole ensemble jump in lockstep.
    """
    rng = np.random.default_rng(seed)
    n = system.n
    J = coupling_matrix(n, system.edges)
    s = np.ones((replicas, n))
    s[:, list(system.init_ones)] = -1.0
    rows = np.arange(replicas)
    history = [s.mean(axis=0)]
    for _ in range(sweeps):
        for _ in range(n):
            sites = rng.integers(n, size=replicas)
            accept = 1.0 / (1.0 + np.exp(flip_cost(s, sites, J, system.h) / temperature))
            flipped = rng.random(replicas) < accept
            s[rows[flipped], sites[flipped]] *= -1.0
        history.append(s.mean(axis=0))
    return np.array(history)
