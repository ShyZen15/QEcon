"""QEcon command line.

    python -m qecon run specs/banks.yaml                 # -> out/<name>.json + out/<name>.png
    python -m qecon run specs/banks.yaml --exact         # overlay exact expm, report Trotter error
    python -m qecon run specs/banks.yaml --set fields.bailout.nodes=[1] --set uncertainty.gamma=0
    python -m qecon validate specs/banks.yaml            # check only, print size/gate summary
    python -m qecon list                                 # available presets
"""
import argparse
import sys

from plugins import REGISTRY

from .spec import SpecError


def _summary_line(s):
    from plugins.common import human_bytes
    return (f"n = {s['n']} | edges = {s['edges']} | statevector = {human_bytes(s['statevector_bytes'])}"
            f" | {s['rzz_per_step']} RZZ (~{s['cx_per_step']} CX) per order-{s['order']} Trotter step,"
            " pre-routing")


def main(argv=None):
    p = argparse.ArgumentParser(prog="qecon", description="Economics -> Ising Hamiltonian -> Trotter circuit")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="validate, simulate, write JSON + PNG")
    r.add_argument("spec")
    r.add_argument("--out", default="out", help="output directory (default: out)")
    r.add_argument("--backend", choices=["local", "cloud"], help="override simulation.backend")
    r.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                   help="override a spec value, e.g. fields.money_growth=12")
    r.add_argument("--name", help="output file stem (default: spec name)")
    r.add_argument("--exact", action="store_true", help="also compute exact evolution (n <= 16)")
    r.add_argument("--baseline", action="store_true",
                   help="also run the same model without the shock; report the excess")
    r.add_argument("--no-plot", action="store_true")

    v = sub.add_parser("validate", help="check a spec without simulating")
    v.add_argument("spec")
    v.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")

    sub.add_parser("list", help="list presets")
    args = p.parse_args(argv)

    if args.cmd == "list":
        for name, cls in REGISTRY.items():
            print(f"{name:10s} |0> = {cls.state_names[0]:12s} |1> = {cls.state_names[1]:12s} "
                  f"headline: {cls.headline}")
        return 0

    from .api import prepare, run_spec, save_result

    try:
        if args.cmd == "validate":
            plugin, spec, warns = prepare(args.spec, args.set)
            for w in warns:
                print("WARNING:", w)
            print("OK:", _summary_line(plugin.gate_summary()))
            return 0

        result = run_spec(args.spec, backend=args.backend, overrides=args.set, exact=args.exact,
                         baseline=args.baseline)
    except SpecError as e:
        print("SpecError:", e, file=sys.stderr)
        return 2

    for w in result["warnings"]:
        print("WARNING:", w)
    print(_summary_line(result["summary"]))
    jpath = save_result(result, args.out, args.name)
    print(f"wrote {jpath}  ({result['runtime_s']} s)")
    key = result["headline"]
    ys = result["series"][key]
    print(f"{key}: t=0 -> {ys[0]:.3f}, peak {max(ys):.3f}, final {ys[-1]:.3f}")
    if "trotter_max_error" in result:
        print(f"max |Trotter - exact| on {key}: {result['trotter_max_error']:.2e}")
    if "baseline" in result:
        b = result["baseline"]["series"][key]
        print(f"baseline (no shock) {key}: peak {max(b):.3f};  "
              f"time-avg excess due to shock {sum(result['excess']['series'][key]) / len(b):+.3f}")
    if not args.no_plot:
        from .plots import plot_result
        print("wrote", plot_result(result, jpath[:-5] + ".png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
