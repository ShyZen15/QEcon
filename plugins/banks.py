"""Preset C: interbank contagion on a cross-holdings network.

Qubit = bank.  |0> = solvent,  |1> = insolvent.

    J_ij  <- symmetrized Elliott-Golub-Jackson dependency matrix
             A = C_hat (I - C)^-1,  C_hat_jj = 1 - sum_i C_ij
             Elliott, Golub & Jackson (2014), "Financial Networks and Contagion",
             American Economic Review 104(10). Ising mapping of EGJ contagion:
             Tomar, Nagpal, Chauhan & Hassan, arXiv:2609.17415 (2026 preprint).
    h_i   <- kappa * (CET1 capital ratio - regulatory minimum)   [> 0 favours solvent]
             Basel III minimum 4.5% CET1 + 2.5% conservation buffer = 7%
             (BCBS, "Basel III: A global regulatory framework...", 2010, rev. 2011).
             Shocked bank: h = -shock (its capital is wiped out).
             Bailout: h += strength on the chosen banks (external control field,
             as in Tomar et al.).
    Gamma <- liquidity / rollover uncertainty.

Honest caveats (also on the slide):
  * Real exposure is directed; a Hermitian ZZ coupling must be symmetric, so we use
    (A_ij + A_ji)/2. That loses direction.
  * Coherent dynamics is reversible: a cascade can partially un-spread. We report the
    time series and its peak, and the shocked bank's negative field keeps it down.
  * kappa, J_scale and Gamma are dimensionless calibration knobs chosen so that
    h, J and Gamma are of comparable size. The literature fixes the structure, not
    these absolute scales.
"""
import numpy as np

from .common import EconPlugin, as_vector


def egj_dependency(C):
    """A = C_hat (I - C)^-1. A_ij = how much bank i's value depends on bank j's assets.
    Columns of A sum to 1 (every unit of j's assets ends up owned by someone)."""
    C = np.asarray(C, dtype=float)
    n = len(C)
    C_hat = np.diag(1.0 - C.sum(axis=0))
    return C_hat @ np.linalg.inv(np.eye(n) - C)


def holdings_matrix(n, holdings):
    C = np.zeros((n, n))
    for holder, issuer, frac in holdings:
        C[int(holder), int(issuer)] = float(frac)
    return C


def coupling_matrix(C, J_scale=1.0):
    """Symmetrize the EGJ dependency, drop self-dependency, scale so max J = J_scale."""
    A = egj_dependency(C)
    S = (A + A.T) / 2.0
    np.fill_diagonal(S, 0.0)
    top = S.max()
    if top > 0:
        S = J_scale * S / top
    return S


class BanksPlugin(EconPlugin):
    name = "banks"
    state_names = ("solvent", "insolvent")
    headline = "fraction_failed"
    headline_label = "Fraction of banks insolvent"
    defaults = {
        "network": {"J_scale": 1.0, "min_coupling": 0.2},
        "fields": {"regulatory_min": 7.0, "kappa": 0.1,
                   "shock": {"nodes": [], "strength": 1.0},
                   "bailout": {"nodes": [], "strength": 2.0}},
    }

    # ---- validator hooks -----------------------------------------------------------
    @staticmethod
    def n_agents(spec):
        return int(spec["agents"]["n"])

    @staticmethod
    def validate_spec(spec, err, warn, check):
        n = check.integer("agents.n", lo=1)
        if n is None:
            return
        check.labels("agents.labels", n)

        hold = check.get("network.holdings")
        if not isinstance(hold, list) or not hold:
            err("network.holdings", "must be a non-empty list of [holder, issuer, fraction]")
        else:
            C = np.zeros((n, n))
            seen = set()
            ok = True
            for k, row in enumerate(hold):
                where = f"network.holdings[{k}]"
                if not (isinstance(row, (list, tuple)) and len(row) == 3):
                    err(where, f"must be [holder, issuer, fraction], got {row!r}")
                    ok = False
                    continue
                a, b, f = row
                if not all(isinstance(v, int) and not isinstance(v, bool) for v in (a, b)):
                    err(where, "holder and issuer must be integers")
                    ok = False
                    continue
                if not (0 <= a < n and 0 <= b < n):
                    err(where, f"index out of range (n = {n})")
                    ok = False
                    continue
                if a == b:
                    err(where, f"bank {a} cannot hold itself")
                    ok = False
                    continue
                if not check.is_number(f) or not (0 < f < 1):
                    err(where, f"fraction must be in (0, 1), got {f!r}")
                    ok = False
                    continue
                if (a, b) in seen:
                    err(where, f"duplicate pair ({a}, {b})")
                    ok = False
                seen.add((a, b))
                C[a, b] = f
            if ok:
                for j, s in enumerate(C.sum(axis=0)):
                    if s >= 1:
                        err("network.holdings",
                            f"column {j} sums to {s:.3f}; must be < 1 "
                            "(EGJ needs outside shareholders, else I - C is singular)")

        check.number("network.J_scale", lo=0, strict=True)
        check.number("network.min_coupling", lo=0, hi=1)
        check.vector("fields.capital_buffer", n)
        check.number("fields.regulatory_min")
        check.number("fields.kappa")
        for knob in ("shock", "bailout"):
            check.indices(f"fields.{knob}.nodes", n)
            check.number(f"fields.{knob}.strength")

    # ---- Snigdha's contract --------------------------------------------------------
    def build_system(self):
        s = self.spec
        n = int(s["agents"]["n"])
        net, f = s["network"], s["fields"]

        C = holdings_matrix(n, net["holdings"])
        S = coupling_matrix(C, float(net["J_scale"]))
        thr = float(net["min_coupling"]) * float(net["J_scale"])
        edges = {(i, j): float(S[i, j])
                 for i in range(n) for j in range(i + 1, n) if S[i, j] >= thr and S[i, j] > 0}

        buffers = np.array(as_vector(f["capital_buffer"], n))
        h = float(f["kappa"]) * (buffers - float(f["regulatory_min"]))
        for k in f["shock"]["nodes"]:
            h[k] = -float(f["shock"]["strength"])
        for k in f["bailout"]["nodes"]:
            h[k] += float(f["bailout"]["strength"])

        gamma = as_vector(s["uncertainty"]["gamma"], n)
        return n, edges, h.tolist(), gamma

    def baseline_overrides(self):
        return ["initial.ones=[]", "fields.shock.nodes=[]"]

    def labels(self):
        n = int(self.spec["agents"]["n"])
        return list(self.spec["agents"].get("labels") or [f"Bank {i}" for i in range(n)])
