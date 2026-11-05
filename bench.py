import sys
import time
from core.engine import compile_ising, run_time_series

n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
print("n =", n)
edges = {(i, i + 1): 1.0 for i in range(n - 1)}
H = compile_ising(n, edges, h=[0.1] * n, gamma=[0.5] * n)
times = [0.1 * k for k in range(1, 11)]

t0 = time.perf_counter()
out = run_time_series(H, times, steps=10, init_ones=(0,))
print("seconds:", time.perf_counter() - t0)
print([float(x[0]) for x in out])
print("qubits in H:", H.num_qubits)

try:
    run_time_series(H, times, steps=10, backend="nonsense")
except ValueError as e:
    print("bad backend handled:", e)