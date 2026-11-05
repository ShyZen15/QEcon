<<<<<<< HEAD
from qiskit import transpile
import warnings
from scipy.sparse import SparseEfficiencyWarning
warnings.filterwarnings("ignore", category=SparseEfficiencyWarning)
=======
>>>>>>> 4e009335b92276a0c1a2f4de7d7ad6e3dcca5710
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


<<<<<<< HEAD
def evolve(H, t, steps, init_ones=(), order=2, unroll=True):
    qc = QuantumCircuit(H.num_qubits)
    for q in init_ones:
        qc.x(q)
    synth = LieTrotter(reps=steps) if order == 1 else SuzukiTrotter(order=order, reps=steps)
    qc.append(PauliEvolutionGate(H, time=t, synthesis=synth), range(H.num_qubits))
    if unroll:
        qc = transpile(qc, basis_gates=["rx", "rz", "rzz", "x", "cx"],
                optimization_level=0)
=======
def evolve(H, t, steps, init_ones=(), order=2):
    qc = QuantumCircuit(H.num_qubits)
    for q in init_ones:
        qc.x(q)  # seed defaults/evaders
    synth = LieTrotter(reps=steps) if order == 1 else SuzukiTrotter(order=order, reps=steps)
    qc.append(PauliEvolutionGate(H, time=t, synthesis=synth), range(H.num_qubits))
>>>>>>> 4e009335b92276a0c1a2f4de7d7ad6e3dcca5710
    return qc


def magnetization(n):
    return SparsePauliOp.from_sparse_list([("Z", [i], 1 / n) for i in range(n)], num_qubits=n)


def exact_state(H, t, init_ones=()):
    psi0 = Statevector.from_int(sum(1 << q for q in init_ones), 2**H.num_qubits)
    A = (-1j * t * H.to_matrix(sparse=True)).tocsc()
<<<<<<< HEAD
    return expm_multiply(A, psi0.data)

def get_estimator(backend="local"):
    """Return an estimator by name. 'local' = exact statevector simulator."""
    if backend == "local":
        return StatevectorEstimator()
    if backend == "cloud":
        # Imported here so a missing cloud setup never breaks local runs
        from qiskit_ibm_runtime import EstimatorV2
        raise NotImplementedError(
            "Cloud needs a runtime session/backend; wire this up once you have an account."
        )
    raise ValueError(f"Unknown backend '{backend}'. Use 'local' or 'cloud'.")


def run_time_series(H, times, steps, init_ones=(), observables=None,
                    backend="local", order=2):
    """One circuit per time value, all sent in a single batched estimator call.
    Returns a list (one entry per time) of arrays of expectation values."""
    if observables is None:
        observables = [magnetization(H.num_qubits)]
    est = get_estimator(backend)
    circuits = [evolve(H, t, steps, init_ones, order) for t in times]
    result = est.run([(qc, observables) for qc in circuits]).result()
    return [np.atleast_1d(r.data.evs) for r in result]
=======
    return expm_multiply(A, psi0.data)
>>>>>>> 4e009335b92276a0c1a2f4de7d7ad6e3dcca5710
