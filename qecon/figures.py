"""Isha's slide figures + the JSON results Arsh's app can load.

    python -m qecon.figures            # -> figures/*.png, results/*.json  (~3 min)
"""
import os

from .api import run_spec, save_result
from .plots import plot_compare, plot_lightcone_pair, plot_result

FIG = "figures"
RES = "results"


def main():
    os.makedirs(FIG, exist_ok=True)

    # ---- banks: shock vs no shock vs bailout -----------------------------------------
    runs = {
        "no shock (baseline)": ["initial.ones=[]", "fields.shock.nodes=[]"],
        "Core-B fails": [],
        "+ bail out Core-A": ["fields.bailout.nodes=[0]"],
        "+ ring-fence Peri-3/4": ["fields.bailout.nodes=[5,6]"],
    }
    res = {}
    for label, ov in runs.items():
        print("banks:", label)
        res[label] = run_spec("specs/banks.yaml", overrides=ov, exact=True)
        print(f"   max |Trotter - exact| = {res[label]['trotter_max_error']:.1e}")
    save_result(res["Core-B fails"], RES, "banks_shock")
    save_result(res["+ bail out Core-A"], RES, "banks_bailout_coreA")
    save_result(res["no shock (baseline)"], RES, "banks_baseline")
    plot_result(res["Core-B fails"], os.path.join(FIG, "banks_shock.png"))
    plot_compare(list(res.values()), list(res.keys()), os.path.join(FIG, "banks_bailout.png"),
                 "Interbank contagion: Core-B fails (8 banks, EGJ cross-holdings)")
    plot_lightcone_pair(res["Core-B fails"], res["+ bail out Core-A"],
                        os.path.join(FIG, "banks_lightcone.png"),
                        "Core-B fails: P(insolvent) by distance from Core-B",
                        "Same shock, Core-A bailed out")

    # ---- firms: money-growth sweep ---------------------------------------------------
    sweep = [2, 8, 14, 20]
    fr = []
    for mu in sweep:
        print("firms: money_growth =", mu)
        fr.append(run_spec("specs/firms.yaml", overrides=[f"fields.money_growth={mu}"]))
        save_result(fr[-1], RES, f"firms_money_{mu}")
    plot_compare(fr, [f"money growth {mu}%" for mu in sweep],
                 os.path.join(FIG, "firms_money_sweep.png"),
                 "Price-setting firms on a 4x3 supply grid: monetary shock")

    # ---- taxpayers (stretch preset) --------------------------------------------------
    tx = []
    for p in (0.02, 0.05, 0.10):
        print("taxpayers: audit_prob =", p)
        tx.append(run_spec("specs/taxpayers.yaml", overrides=[f"fields.audit_prob={p}"]))
    save_result(tx[1], RES, "taxpayers")
    plot_compare(tx, [f"audit prob {p:.0%}" for p in (0.02, 0.05, 0.10)],
                 os.path.join(FIG, "taxpayers_audit.png"),
                 "Tax compliance (Zaklan model, coherent): evader cluster in a 4x3 lattice")
    print("done")


if __name__ == "__main__":
    main()
