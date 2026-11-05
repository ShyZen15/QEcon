import warnings
from scipy.sparse import SparseEfficiencyWarning
warnings.filterwarnings("ignore", category=SparseEfficiencyWarning)
import numpy as np
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import Statevector
from core.engine import compile_ising, evolve, magnetization, exact_state

# 1. Build the system: 4 agents in a chain
n = 4
edges = {(0, 1): 1.0, (1, 2): 1.0, (2, 3): 1.0}
H = compile_ising(n, edges, h=[0.1] * n, gamma=[0.5] * n)

# 2. Build one circuit for t = 1.0, with agent 0 starting as "defaulted"
qc = evolve(H, t=1.0, steps=20, init_ones=(0,))

# 3. Measure average magnetization
M = magnetization(n)
est = StatevectorEstimator()
trotter_value = float(est.run([(qc, M)]).result()[0].data.evs)

# 4. Compare against the exact answer
psi_exact = exact_state(H, t=1.0, init_ones=(0,))
exact_value = float(np.real(psi_exact.conj() @ (M.to_matrix(sparse=True) @ psi_exact)))

print("Trotter:", trotter_value)
print("Exact:  ", exact_value)
print("Error:  ", abs(trotter_value - exact_value))

# Fidelity error: 1 - |<exact|trotter>|^2
psi_trot = Statevector(qc).data
print("State error:", 1 - abs(np.vdot(psi_exact, psi_trot)) ** 2)