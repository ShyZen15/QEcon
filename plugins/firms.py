"""Preset A: firms setting prices on a 2D supply grid (inflation expectations).

Qubit = firm.  |0> = hold price,  |1> = raise price.

    J     <- strategic complementarity in price setting: you raise if your neighbours
             raise. Cooper & John (1988), "Coordinating Coordination Failures in
             Keynesian Models", QJE 103(3); Ball & Romer (1991), "Sticky Prices as
             Coordination Failure", AER 81(3).
    h_i   <- anchor * credibility                     (anchored expectations -> hold)
             - beta * (money_growth - target)         (expansionary money -> raise)
             - tau  * vat_change                      (cost-push tax -> raise)
             + sigma * N(0, 1)                        (heterogeneous firms)
             The disorder term is the random-field Ising model, Bouchaud (2013),
             "Crises and collective socio-economic phenomena", J. Stat. Phys. 151.
    Gamma <- uncertainty about rivals' pricing.

Observable: inflation pressure = fraction of firms raising = (1 - <M>)/2.

The grid is 2D on purpose: a 1D transverse-field Ising chain is free-fermion solvable,
a 2D grid plus a longitudinal field is not. beta, tau, anchor and Gamma are
dimensionless calibration knobs (defaults: 10pp excess money growth ~ one unit of J).
"""
import numpy as np

from .common import EconPlugin, as_vector, grid_edges, grid_positions


def firm_fields(n, f):
    h = (float(f["anchor"]) * float(f["credibility"])
         - float(f["beta"]) * (float(f["money_growth"]) - float(f["target"]))
         - float(f["tau"]) * float(f["vat_change"]))
    h = np.full(n, h)
    d = f.get("disorder") or {}
    sigma = float(d.get("sigma", 0.0))
    if sigma:
        h += sigma * np.random.default_rng(int(d.get("seed", 0))).standard_normal(n)
    return h


class FirmsPlugin(EconPlugin):
    name = "firms"
    state_names = ("hold price", "raise price")
    headline = "inflation_pressure"
    headline_label = "Inflation pressure (fraction of firms raising)"
    defaults = {
        "network": {"J": 1.0},
        "fields": {"credibility": 0.8, "anchor": 1.0, "money_growth": 2.0, "target": 2.0,
                   "beta": 0.1, "vat_change": 0.0, "tau": 0.05,
                   "disorder": {"sigma": 0.0, "seed": 0}},
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
        n = g[0] * g[1]
        if min(g) == 1:
            warn.append("agents.grid is 1 wide: that's a 1D chain (classically easier); "
                        "use a 2D grid for the demo")
        check.labels("agents.labels", n)
        check.number("network.J")
        check.number("fields.credibility", lo=0, hi=1)
        for k in ("anchor", "money_growth", "target", "beta", "vat_change", "tau"):
            check.number(f"fields.{k}")
        check.number("fields.disorder.sigma", lo=0)

    def build_system(self):
        Lx, Ly = self.spec["agents"]["grid"]
        n = Lx * Ly
        J = float(self.spec["network"]["J"])
        edges = {pair: J for pair in grid_edges(Lx, Ly)}
        h = firm_fields(n, self.spec["fields"])
        gamma = as_vector(self.spec["uncertainty"]["gamma"], n)
        return n, edges, h.tolist(), gamma

    def baseline_overrides(self):
        # same economy, money growth on target and no tax change
        return [f"fields.money_growth={self.spec['fields']['target']}", "fields.vat_change=0"]

    def labels(self):
        Lx, Ly = self.spec["agents"]["grid"]
        return list(self.spec["agents"].get("labels")
                    or [f"Firm ({x},{y})" for y in range(Ly) for x in range(Lx)])

    def positions(self):
        Lx, Ly = self.spec["agents"]["grid"]
        return grid_positions(Lx, Ly)
