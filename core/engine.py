import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector, partial_trace, entropy
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.synthesis import SuzukiTrotter, LieTrotter
from qiskit.primitives import StatevectorEstimator
from scipy.sparse.linalg import expm_multiply


def compile_ising(n, edges, h, gamma):
    """edges: {(i,j): J}. Index-based -> no endianness bugs."""
    terms  = [("ZZ", [i, j], -J) for (i, j), J in edges.items()]
    terms += [("Z", [i], -h[i]) for i in range(n) if h[i]]
    terms += [("X", [i], -gamma[i]) for i in range(n) if gamma[i]]
    return SparsePauliOp.from_sparse_list(terms, num_qubits=n).simplify()


def evolve(H, t, steps, init_ones=(), order=2):
    qc = QuantumCircuit(H.num_qubits)
    for q in init_ones:
        qc.x(q)  # seed defaults/evaders
    synth = LieTrotter(reps=steps) if order == 1 else SuzukiTrotter(order=order, reps=steps)
    qc.append(PauliEvolutionGate(H, time=t, synthesis=synth), range(H.num_qubits))
    return qc


def magnetization(n):
    return SparsePauliOp.from_sparse_list([("Z", [i], 1 / n) for i in range(n)], num_qubits=n)


def exact_state(H, t, init_ones=()):
    psi0 = Statevector.from_int(sum(1 << q for q in init_ones), 2**H.num_qubits)
    A = (-1j * t * H.to_matrix(sparse=True)).tocsc()
    return expm_multiply(A, psi0.data)