"""Preset B: tax compliance (a quantum version of the Zaklan Ising model).

Qubit = taxpayer.  |0> = comply,  |1> = evade.

    J     <- social influence / conditional cooperation (Gächter; Frey & Torgler).
             Zaklan, Westerhoff & Stauffer (2009), "Analysing tax evasion dynamics via
             the Ising model", J. Econ. Interact. Coord. 4: 2D lattice, +1 honest, -1 evader.
    h_i   <- morale + enforcement * (audit_prob * penalty) - tax_burden * (tax_rate - ref_rate)
             Zaklan's two enforcement knobs are audit probability p and penalty k
             (periods a caught evader must stay honest). In their model k acts through
             the dynamics; here we fold the expected penalty p*k into a static field.
             That is a modeling simplification, stated as such.
    Gamma <- ambivalence.

Observable: compliance rate = (1 + <M>)/2.
"""
import numpy as np

from .common import EconPlugin, as_vector, grid_edges, grid_positions


class TaxpayersPlugin(EconPlugin):
    name = "taxpayers"
    state_names = ("comply", "evade")
    headline = "compliance_rate"
    headline_label = "Compliance rate"
    headline_from_zero = True
    defaults = {
        "network": {"J": 1.0},
        "fields": {"morale": 0.2, "audit_prob": 0.05, "penalty": 10, "enforcement": 1.0,
                   "tax_rate": 30.0, "ref_rate": 30.0, "tax_burden": 0.05},
    }

    @staticmethod
    def n_agents(spec):
        Lx, Ly = spec["agents"]["grid"]
        return int(Lx) * int(Ly)

    @staticmethod
    def validate_spec(spec, err, warn, check):
        g = check.get("agents.grid")
        if not (isinstance(g, list) and len(g) == 2
                and all(isinstance(v, int) and not isinstance(v, bool) and v >= 1 for v in g)):
            err("agents.grid", f"must be [Lx, Ly] with positive integers, got {g!r}")
            return
        check.labels("agents.labels", g[0] * g[1])
        check.number("network.J")
        check.number("fields.audit_prob", lo=0, hi=1)
        check.number("fields.penalty", lo=0)
        for k in ("morale", "enforcement", "tax_rate", "ref_rate", "tax_burden"):
            check.number(f"fields.{k}")

    def build_system(self):
        Lx, Ly = self.spec["agents"]["grid"]
        n = Lx * Ly
        f = self.spec["fields"]
        edges = {pair: float(self.spec["network"]["J"]) for pair in grid_edges(Lx, Ly)}
        h_val = (float(f["morale"])
                 + float(f["enforcement"]) * float(f["audit_prob"]) * float(f["penalty"])
                 - float(f["tax_burden"]) * (float(f["tax_rate"]) - float(f["ref_rate"])))
        h = np.full(n, h_val)
        gamma = as_vector(self.spec["uncertainty"]["gamma"], n)
        return n, edges, h.tolist(), gamma

    def labels(self):
        Lx, Ly = self.spec["agents"]["grid"]
        return [f"Taxpayer ({x},{y})" for y in range(Ly) for x in range(Lx)]

    def positions(self):
        Lx, Ly = self.spec["agents"]["grid"]
        return grid_positions(Lx, Ly)
