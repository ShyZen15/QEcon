"""YAML spec loading + validation.

The validator collects EVERY problem and raises once, before anything expensive
(Hamiltonian, circuits, estimator) runs:

    SpecError: 3 problems in specs/banks.yaml
      - network.holdings[4]: index out of range (n = 8)
      - network.holdings: column 0 sums to 1.050; must be < 1 ...
      - initial.ones: 5 listed twice
"""
import copy
import difflib
import math

import yaml

COMMON_DEFAULTS = {
    "uncertainty": {"gamma": 0.5},
    "initial": {"ones": []},
    "simulation": {"t_max": 4.0, "n_times": 21, "steps": 12, "order": 1, "backend": "local"},
    "sources": {},
}

MAX_AGENTS = 24          # statevector = 16 * 2^n bytes: 24 agents = 256 MB per state
DEMO_AGENTS = 16         # above this a live demo gets slow


class SpecError(Exception):
    pass


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_spec(path):
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise SpecError(f"{path}: top level must be a mapping, got {type(raw).__name__}")
    raw["_path"] = str(path)
    return raw


def with_defaults(spec):
    """Common defaults, then the preset's own defaults, then the user's values."""
    from plugins import REGISTRY
    plugin_cls = REGISTRY.get(spec.get("preset"))
    merged = deep_merge(COMMON_DEFAULTS, getattr(plugin_cls, "defaults", {}))
    return deep_merge(merged, spec)


def apply_overrides(spec, assignments):
    """['fields.bailout.nodes=[1]', 'uncertainty.gamma=0'] -> mutated copy.
    Values are parsed with yaml.safe_load, so lists, numbers and booleans all work."""
    spec = copy.deepcopy(spec)
    for a in assignments or []:
        if "=" not in a:
            raise SpecError(f"--set {a!r}: expected key.path=value")
        key, val = a.split("=", 1)
        node = spec
        parts = key.strip().split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
            if not isinstance(node, dict):
                raise SpecError(f"--set {a!r}: {p} is a single value, so it has no keys")
        node[parts[-1]] = yaml.safe_load(val)
    return spec


def unknown_keys(spec, plugin_cls, err):
    """A typo like fields.kapa would otherwise be ignored and the default used silently."""
    defaults = plugin_cls.defaults
    known = {
        "": {"preset", "name", "agents", "network", "fields", "uncertainty", "initial",
             "simulation", "sources"},
        "network": set(defaults.get("network", {})) | set(plugin_cls.extra_network),
        "fields": set(defaults.get("fields", {})) | set(plugin_cls.extra_fields),
        "uncertainty": set(COMMON_DEFAULTS["uncertainty"]),
        "initial": set(COMMON_DEFAULTS["initial"]),
        "simulation": set(COMMON_DEFAULTS["simulation"]) | {"dt"},
    }
    for section, allowed in known.items():
        node = spec.get(section) if section else spec
        if not isinstance(node, dict):
            continue
        for key in node:
            if str(key).startswith("_") or key in allowed:
                continue
            guess = difflib.get_close_matches(str(key), allowed, n=1)
            where = f"{section}.{key}" if section else str(key)
            err(where, "unknown key" + (f" (did you mean {guess[0]}?)" if guess else ""))


class Check:
    """Small typed-lookup helper handed to each plugin's validate_spec."""

    def __init__(self, spec, err):
        self.spec = spec
        self.err = err

    MISSING = object()

    def get(self, path, default=MISSING):
        node = self.spec
        for p in path.split("."):
            if not isinstance(node, dict) or p not in node:
                if default is not Check.MISSING:
                    return default
                return Check.MISSING
            node = node[p]
        return node

    @staticmethod
    def is_number(v):
        return (isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(float(v)))

    def number(self, path, lo=None, hi=None, strict=False):
        v = self.get(path)
        if v is Check.MISSING:
            self.err(path, "missing")
            return None
        if not self.is_number(v):
            self.err(path, f"must be a finite number, got {v!r}")
            return None
        if lo is not None and (v <= lo if strict else v < lo):
            self.err(path, f"must be {'>' if strict else '>='} {lo}, got {v}")
            return None
        if hi is not None and v > hi:
            self.err(path, f"must be <= {hi}, got {v}")
            return None
        return float(v)

    def integer(self, path, lo=None, hi=None):
        v = self.get(path)
        if v is Check.MISSING:
            self.err(path, "missing")
            return None
        if not isinstance(v, int) or isinstance(v, bool):
            self.err(path, f"must be an integer, got {v!r}")
            return None
        if lo is not None and v < lo:
            self.err(path, f"must be >= {lo}, got {v}")
            return None
        if hi is not None and v > hi:
            self.err(path, f"must be <= {hi}, got {v}")
            return None
        return v

    def vector(self, path, n, lo=None):
        """Scalar or list of length n, all finite numbers."""
        v = self.get(path)
        if v is Check.MISSING:
            self.err(path, "missing")
            return
        vals = v if isinstance(v, list) else [v]
        if isinstance(v, list) and len(v) != n:
            self.err(path, f"has {len(v)} entries, expected {n} (one per agent) or a single number")
            return
        for k, x in enumerate(vals):
            where = f"{path}[{k}]" if isinstance(v, list) else path
            if not self.is_number(x):
                self.err(where, f"must be a finite number, got {x!r}")
            elif lo is not None and x < lo:
                self.err(where, f"must be >= {lo}, got {x}")

    def indices(self, path, n):
        v = self.get(path, [])
        if not isinstance(v, list):
            self.err(path, f"must be a list of agent indices, got {v!r}")
            return
        seen = set()
        for k, q in enumerate(v):
            if not isinstance(q, int) or isinstance(q, bool):
                self.err(f"{path}[{k}]", f"must be an integer index, got {q!r}")
            elif not 0 <= q < n:
                self.err(f"{path}[{k}]", f"agent {q} out of range (n = {n})")
            elif q in seen:
                self.err(path, f"{q} listed twice")
            seen.add(q)

    def labels(self, path, n):
        v = self.get(path, None)
        if v is None:
            return
        if not isinstance(v, list) or len(v) != n:
            self.err(path, f"must be a list of {n} names")


def validate(spec):
    """Fill defaults, check everything, raise SpecError listing all problems.
    Returns (spec_with_defaults, warnings)."""
    from plugins import REGISTRY

    path = spec.get("_path", "<spec>")
    errs, warns = [], []

    def err(where, msg):
        errs.append(f"{where}: {msg}")

    preset = spec.get("preset")
    if preset not in REGISTRY:
        raise SpecError(f"1 problem in {path}\n  - preset: {preset!r} is not one of "
                        f"{sorted(REGISTRY)}")
    spec = with_defaults(spec)
    plugin_cls = REGISTRY[preset]
    check = Check(spec, err)

    if not isinstance(spec.get("name", preset), str):
        err("name", "must be a string")
    unknown_keys(spec, plugin_cls, err)

    # preset-specific structure first: it tells us n
    try:
        plugin_cls.validate_spec(spec, err, warns, check)
    except (KeyError, TypeError, ValueError) as e:
        err("<structure>", f"could not read spec ({type(e).__name__}: {e})")

    n = None
    try:
        n = plugin_cls.n_agents(spec)
        if not isinstance(n, int) or n < 1:
            n = None
    except Exception as e:  # noqa: BLE001  (any shape problem -> spec error)
        if not any(e_.startswith("agents") for e_ in errs):
            err("agents", f"could not determine number of agents ({e})")

    if n is not None:
        if n > MAX_AGENTS:
            size = f"{2.0 ** (n - 26):.1f} GiB" if n < 100 else "more memory than exists"
            err("agents", f"{n} agents needs {size} per statevector "
                          f"(16 * 2^n bytes); limit is {MAX_AGENTS}")
        elif n > DEMO_AGENTS:
            warns.append(f"{n} agents: fine offline, slow for a live demo (> {DEMO_AGENTS})")
        check.vector("uncertainty.gamma", n, lo=0)
        check.indices("initial.ones", n)

    check.number("simulation.t_max", lo=0)
    check.integer("simulation.n_times", lo=2)
    if check.get("simulation.dt", None) is not None:
        check.number("simulation.dt", lo=0, strict=True)
    else:
        check.integer("simulation.steps", lo=1)
    order = check.get("simulation.order")
    if order not in (1, 2):
        err("simulation.order", f"must be 1 (Lie-Trotter) or 2 (Suzuki-Trotter), got {order!r}")
    backend = check.get("simulation.backend")
    if backend not in ("local", "cloud"):
        err("simulation.backend", f"must be 'local' or 'cloud', got {backend!r}")

    if errs:
        raise SpecError(f"{len(errs)} problem{'s' if len(errs) != 1 else ''} in {path}\n  - "
                        + "\n  - ".join(errs))

    # ---- warnings that need the built system (cheap: no circuits yet) ---------------
    plugin = plugin_cls(spec)
    n, edges, h, gamma = plugin.system()
    if all(g == 0 for g in gamma):
        warns.append("gamma = 0 everywhere: all terms commute, nothing will move "
                     "(this is the classical limit)")
    G = plugin.graph()
    if n > 1 and not __import__("networkx").is_connected(G):
        comps = __import__("networkx").number_connected_components(G)
        warns.append(f"interaction graph has {comps} disconnected pieces: some agents never "
                     "feel the shock")
    degrees = [d for _, d in G.degree()]
    is_chain = n > 2 and len(edges) == n - 1 and max(degrees, default=0) <= 2
    if is_chain and all(x == 0 for x in h):
        warns.append("1D chain with h = 0 is free-fermion solvable (Jordan-Wigner): add a "
                     "field or use a 2D graph")
    return spec, warns
