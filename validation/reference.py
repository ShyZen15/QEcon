"""Ground truth that shares no code with the thing it checks.

core.engine.exact_state builds its matrix from the same SparsePauliOp the circuit
uses, so a bug in compile_ising would appear on both sides and cancel. Everything
here starts from the raw (edges, h, gamma) and uses only NumPy and SciPy.

Convention: bit i of a basis index is qubit i, and |0> means Z = +1.
"""
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import expm_multiply


def spins(n):
    """Array of shape (n, 2^n): the Z eigenvalue of qubit i in each basis state."""
    idx = np.arange(1 << n)
    return np.array([1 - 2 * ((idx >> i) & 1) for i in range(n)])


def diagonal_energy(n, edges, h):
    """-sum J s_i s_j - sum h s_i for every basis state."""
    s = spins(n)
    energy = np.zeros(1 << n)
    for (i, j), J in edges.items():
        energy -= J * s[i] * s[j]
    for i in range(n):
        energy -= h[i] * s[i]
    return energy


def hamiltonian(n, edges, h, gamma):
    """H = -sum J Z_i Z_j - sum h Z_i - sum Gamma X_i as a sparse matrix."""
    dim = 1 << n
    idx = np.arange(dim)
    H = sp.diags(diagonal_energy(n, edges, h)).tocsr().astype(complex)
    for i in range(n):
        if gamma[i]:
            flip = sp.csr_matrix(
                (np.full(dim, -gamma[i], dtype=complex), (idx ^ (1 << i), idx)),
                shape=(dim, dim),
            )
            H = H + flip
    return H.tocsc()


def basis_state(n, init_ones=()):
    psi = np.zeros(1 << n, dtype=complex)
    psi[sum(1 << q for q in init_ones)] = 1.0
    return psi


def exact_evolve(system, t):
    """exp(-itH)|init>, built without Qiskit."""
    H = hamiltonian(system.n, system.edges, system.h, system.gamma)
    return expm_multiply(-1j * t * H, basis_state(system.n, system.init_ones))


def exact_series(system, times):
    """Exact states at each time. Rows follow `times`."""
    H = hamiltonian(system.n, system.edges, system.h, system.gamma)
    psi0 = basis_state(system.n, system.init_ones)
    return np.array([expm_multiply(-1j * t * H, psi0) for t in times])


def infidelity(a, b):
    """1 - |<a|b>|^2. Rounding can make this about -1e-15, so don't take its log raw."""
    return 1.0 - abs(np.vdot(a, b)) ** 2


def z_expectations(psi, n):
    """<Z_i> for every qubit, from the probabilities."""
    return spins(n) @ (np.abs(psi) ** 2)


def magnetization(psi, n):
    return float(z_expectations(psi, n).mean())


def zz_expectation(psi, n, i, j):
    s = spins(n)
    return float((s[i] * s[j]) @ (np.abs(psi) ** 2))


def x_bar(psi, n):
    """Average <X_i>. Off-diagonal, so it sees phases that Z-basis numbers cannot."""
    idx = np.arange(1 << n)
    return float(np.mean([np.real(np.vdot(psi, psi[idx ^ (1 << i)])) for i in range(n)]))


def half_entropy(psi, n, k=None):
    """Entanglement entropy in bits between qubits 0..k-1 and the rest.

    Basis index = high_bits * 2^k + low_bits, so reshaping to (2^(n-k), 2^k) puts the
    kept qubits on the columns. Schmidt weights are the squared singular values.
    """
    k = n // 2 if k is None else k
    weights = np.linalg.svd(psi.reshape(1 << (n - k), 1 << k), compute_uv=False) ** 2
    weights = weights[weights > 1e-14]
    return max(0.0, float(-(weights * np.log2(weights)).sum()))


def slope(steps, values, fit_from):
    """Log-log slope using only points with steps >= fit_from."""
    r = np.array(steps, dtype=float)
    y = np.array(values, dtype=float)
    keep = r >= fit_from
    return float(np.polyfit(np.log(r[keep]), np.log(y[keep]), 1)[0])
