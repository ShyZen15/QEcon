"""Shared pieces for the economics plugins.

Every preset compiles to the same Hamiltonian (Snigdha's core/engine.py):

    H = - sum_(i,j) J_ij Z_i Z_j  - sum_i h_i Z_i  - sum_i Gamma_i X_i

Conventions (frozen for the whole team):
    |0>  (Z = +1)  = solvent / comply / hold price      ("good" state)
    |1>  (Z = -1)  = failed  / evade  / raise price
    h_i > 0  pushes agent i toward |0>,  h_i < 0 pushes toward |1>
    J_ij > 0 means i and j want to be in the same state (contagion, imitation,
             strategic complementarity)
    edges are {(i, j): J} with integer indices and i < j, never label strings
"""
import networkx as nx
import numpy as np
from qiskit.quantum_info import SparsePauliOp

from core.engine import Plugin, compile_ising, evolve, magnetization


def as_vector(value, n):
    """Scalar -> length-n list; list stays a list. Shape is checked by the validator."""
    if isinstance(value, (list, tuple, np.ndarray)):
        return [float(v) for v in value]
    return [float(value)] * n


def grid_edges(Lx, Ly):
    """Nearest-neighbour edges of an Lx x Ly grid. Agent (x, y) has index y*Lx + x.
    Edge count = Ly(Lx-1) + Lx(Ly-1)."""
    idx = lambda x, y: y * Lx + x
    pairs = []
    for y in range(Ly):
        for x in range(Lx):
            if x + 1 < Lx:
                pairs.append((idx(x, y), idx(x + 1, y)))
            if y + 1 < Ly:
                pairs.append((idx(x, y), idx(x, y + 1)))
    return pairs


def grid_positions(Lx, Ly):
    return {y * Lx + x: [float(x), float(-y)] for y in range(Ly) for x in range(Lx)}


def z_op(i, n):
    return SparsePauliOp.from_sparse_list([("Z", [i], 1.0)], num_qubits=n)


def mean_zz_op(edges, n):
    """(1/|E|) sum_(i,j) Z_i Z_j  -- 'synchronization' between neighbours."""
    if not edges:
        return SparsePauliOp.from_sparse_list([("", [], 0.0)], num_qubits=n)
    w = 1.0 / len(edges)
    return SparsePauliOp.from_sparse_list([("ZZ", [i, j], w) for (i, j) in edges], num_qubits=n)


class EconPlugin(Plugin):
    """Base for every economics preset. Subclasses implement:

        n_agents(spec)            -> int (before building, for the validator)
        validate_spec(spec, err, warn)
        build_system()            -> (n, edges, h, gamma)       [Snigdha's contract]
        labels(), positions()

    and set the class attributes below to name things in economic language.
    """

    name = "econ"
    state_names = ("state 0", "state 1")      # what |0> and |1> mean
    headline = "fraction_one"                 # name of (1 - <M>)/2 in the output
    headline_label = "Fraction in |1>"
    headline_from_zero = False                # True -> report (1 + <M>)/2 instead

    def __init__(self, spec):
        self.spec = spec
        self._system = None

    # ---- Snigdha's Plugin contract -------------------------------------------------
    def init_ones(self):
        return tuple(int(q) for q in self.spec.get("initial", {}).get("ones", []))

    def observables(self, n):
        """[M, Z_0 .. Z_{n-1}, mean ZZ over edges]."""
        _, edges, _, _ = self.system()
        return [magnetization(n)] + [z_op(i, n) for i in range(n)] + [mean_zz_op(edges, n)]

    # ---- helpers -------------------------------------------------------------------
    def system(self):
        if self._system is None:
            self._system = self.build_system()
        return self._system

    def hamiltonian(self):
        n, edges, h, gamma = self.system()
        return compile_ising(n, edges, h, gamma)

    def labels(self):
        n = self.system()[0]
        return [f"Agent {i}" for i in range(n)]

    def positions(self):
        n, edges, _, _ = self.system()
        G = nx.Graph()
        G.add_nodes_from(range(n))
        G.add_edges_from(edges)
        # Kamada-Kawai (graph-distance based) spreads core-periphery structure cleanly;
        # fall back to a seeded spring layout for disconnected graphs.
        try:
            pos = nx.kamada_kawai_layout(G) if nx.is_connected(G) else nx.spring_layout(G, seed=0)
        except Exception:  # noqa: BLE001
            pos = nx.spring_layout(G, seed=0)
        return {i: [float(p[0]), float(p[1])] for i, p in pos.items()}

    def graph(self):
        n, edges, _, _ = self.system()
        G = nx.Graph()
        G.add_nodes_from(range(n))
        G.add_edges_from(edges)
        return G

    def distance_from_seed(self):
        """Graph distance (hops) from the nearest seeded agent; -1 if unreachable.
        With no seed, every agent gets 0. Arsh sorts the light-cone heatmap by this."""
        n = self.system()[0]
        seeds = list(self.init_ones())
        if not seeds:
            return [0] * n
        d = nx.multi_source_dijkstra_path_length(self.graph(), seeds, weight=None)
        return [int(d.get(i, -1)) for i in range(n)]

    def gate_summary(self):
        """Memory for exact simulation and two-qubit gates per Trotter step (pre-routing)."""
        n, edges, _, _ = self.system()
        sim = self.spec["simulation"]
        qc = evolve(self.hamiltonian(), 1.0, 1, (), sim["order"])
        ops = qc.count_ops()
        # Qiskit emits RZZ normally, but CX+RZ when all terms commute (Gamma = 0):
        # count every two-qubit gate in CX units (RZZ = CX . RZ . CX).
        rzz = ops.get("rzz", 0)
        cx_equiv = 2 * rzz + sum(ops.get(g, 0) for g in ("cx", "cz", "ecr"))
        return {
            "n": n,
            "edges": len(edges),
            "statevector_bytes": 16 * 2 ** n,
            "rzz_per_step": int(rzz),
            "cx_per_step": int(cx_equiv),
            "order": sim["order"],
        }

    def baseline_overrides(self):
        """Overrides that remove the shock but keep everything else, so
        (shocked run) - (baseline run) isolates the effect of the shock from the
        Gamma-driven fluctuations every agent has anyway."""
        return ["initial.ones=[]"]

    def interpret(self, times, evs):
        """evs: (T, n + 2) array of [<M>, <Z_0..Z_{n-1}>, <mean ZZ>] -> economic series."""
        evs = np.asarray(evs, dtype=float)
        n = self.system()[0]
        M = evs[:, 0]
        Z = evs[:, 1:1 + n]
        ZZ = evs[:, 1 + n]
        p_one = (1.0 - Z) / 2.0
        headline = (1.0 + M) / 2.0 if self.headline_from_zero else (1.0 - M) / 2.0
        return {
            "series": {
                self.headline: headline.tolist(),
                "magnetization": M.tolist(),
                "synchronization": ZZ.tolist(),
            },
            "per_agent": {"p_one": p_one.tolist()},
        }


def human_bytes(b):
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if b < 1024 or unit == "PB":
            return f"{b:.0f} {unit}" if unit == "B" else f"{b:.1f} {unit}"
        b /= 1024
