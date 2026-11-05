import numpy as np
from qiskit.quantum_info import Statevector
from core.engine import compile_ising, evolve, exact_state

n = 6
edges = {(i, i + 1): 1.0 for i in range(n - 1)}
H = compile_ising(n, edges, [0.1] * n, [0.5] * n)
exact = exact_state(H, 1.0, (0,))

for steps in (1, 2, 5, 20):
    psi = Statevector(evolve(H, 1.0, steps, (0,))).data
    print(steps, 1 - abs(np.vdot(exact, psi)) ** 2)