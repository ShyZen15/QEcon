"""QEcon live demo for Streamlit.

    streamlit run demo/streamlit_app.py

Runs through demo.server.api_run, the same path as the local web demo, so levers,
counterfactuals and hardware matching behave identically in both. Everything runs on
the statevector simulator. Hardware points appear only when results/hardware/ has a run
for the current settings.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import streamlit as st  # noqa: E402
import yaml  # noqa: E402

from demo import charts  # noqa: E402
from demo.server import api_run, base_spec  # noqa: E402
from plugins.common import human_bytes  # noqa: E402
from qecon.api import prepare, run_spec, trotter_schedule  # noqa: E402
from qecon.spec import SpecError  # noqa: E402

# A public app shares one small machine, so the spec editor gets tighter limits than the
# command line. Each extra agent doubles the memory and the time.
PUBLIC_MAX_AGENTS = 14
PUBLIC_MAX_TIMES = 61
PUBLIC_MAX_T = 30.0
PUBLIC_MAX_STEPS = 600

SCENARIOS = {
    "banks": {
        "tab": "Contagion",
        "title": "Interbank contagion",
        "baseline": "no shock",
        "dek": "Eight banks linked by cross-holdings (Elliott–Golub–Jackson). Each bank is a "
               "qubit: |0⟩ solvent, |1⟩ insolvent. One bank's capital is wiped out and losses "
               "travel along exposures.",
        "mapping": [("J · ZZ", "exposure between banks (symmetrised EGJ dependency matrix)"),
                    ("h · Z", "capital above the Basel III 7% minimum, −2 on the failed bank, plus any bailout"),
                    ("Γ · X", "liquidity and rollover uncertainty")],
    },
    "firms": {
        "tab": "Inflation",
        "title": "Inflation expectations",
        "baseline": "money on target",
        "dek": "Twelve firms on a 4 × 3 supply grid. A firm raises its price when its neighbours "
               "do. Money growth above the 2% target tilts every firm toward raising, and "
               "credibility anchors them.",
        "mapping": [("J · ZZ", "strategic complementarity in pricing between supply-chain neighbours"),
                    ("h · Z", "anchor × credibility − 0.1 × (money growth − 2%) − 0.05 × ΔVAT"),
                    ("Γ · X", "uncertainty about rivals' pricing")],
    },
    "taxpayers": {
        "tab": "Compliance",
        "title": "Tax compliance",
        "baseline": "no evaders",
        "dek": "Twelve taxpayers on a lattice, three evading at the start: the Zaklan Ising "
               "model, made coherent. Audits and penalties add a compliance field, and a higher "
               "tax rate pushes the other way.",
        "mapping": [("J · ZZ", "social influence and conditional cooperation between neighbours"),
                    ("h · Z", "tax morale + audit probability × penalty − 0.05 × (tax rate − 30%)"),
                    ("Γ · X", "ambivalence")],
    },
}


def public_limit_errors(spec):
    """Raises SpecError for an invalid spec. Returns a list of reasons it is too big to host."""
    plugin, checked, _ = prepare(spec)
    sim = checked["simulation"]
    n = plugin.system()[0]
    t_max, n_times = float(sim["t_max"]), int(sim["n_times"])
    problems = []
    if n > PUBLIC_MAX_AGENTS:
        problems.append(f"{n} agents: the hosted app allows {PUBLIC_MAX_AGENTS}. "
                        "Larger runs work from the command line.")
    if n_times > PUBLIC_MAX_TIMES:
        problems.append(f"simulation.n_times = {n_times}: the hosted app allows {PUBLIC_MAX_TIMES}.")
    if t_max > PUBLIC_MAX_T:
        problems.append(f"simulation.t_max = {t_max:g}: the hosted app allows {PUBLIC_MAX_T:g}.")
    if not problems:
        steps, block = trotter_schedule(sim, np.linspace(0.0, t_max, n_times))
        cost = steps[-1] if block else sum(steps)
        if cost > PUBLIC_MAX_STEPS:
            problems.append(f"{cost} Trotter steps: the hosted app allows {PUBLIC_MAX_STEPS}. "
                            "Use a larger simulation.dt or fewer time points.")
    return problems


def number(value, decimals=2):
    """Lever value as YAML text. Rounding removes float noise such as 0.6000000000000001,
    so the default levers still match the cached hardware run."""
    return repr(round(float(value), decimals))


def bank_levers(spec):
    labels = spec["agents"]["labels"]
    f = spec["fields"]
    st.sidebar.subheader("Shock")
    seed_name = st.sidebar.selectbox("Bank that fails", labels, index=f["shock"]["nodes"][0],
                                     key="banks.seed")
    seed = labels.index(seed_name)
    st.sidebar.subheader("Policy")
    # The key includes the seed, so a failed bank can never stay selected for a bailout.
    bail_names = st.sidebar.multiselect("Bail out", [x for x in labels if x != seed_name],
                                        key=f"banks.bail.{seed}",
                                        help="Adds an extra solvency field to these banks")
    bail = sorted(labels.index(x) for x in bail_names)
    size = st.sidebar.slider("Bailout size", 0.0, 4.0, float(f["bailout"]["strength"]), 0.25,
                             key="banks.size", help="Extra solvency field, in units of J")
    kappa = st.sidebar.slider("Capital sensitivity κ", 0.0, 0.3, float(f["kappa"]), 0.01,
                              key="banks.kappa", help="h = κ × (CET1 − 7%)")
    levers = {"seed": seed, "bail": bail}
    overrides = [f"initial.ones=[{seed}]", f"fields.shock.nodes=[{seed}]",
                 f"fields.bailout.nodes={bail}", f"fields.bailout.strength={number(size)}",
                 f"fields.kappa={number(kappa)}"]
    return levers, overrides


def firm_levers(spec):
    f = spec["fields"]
    st.sidebar.subheader("Monetary policy")
    money = st.sidebar.slider("Money-supply growth (%)", 0.0, 25.0, float(f["money_growth"]), 1.0,
                              key="firms.money")
    cred = st.sidebar.slider("Central-bank credibility", 0.0, 1.0, float(f["credibility"]), 0.05,
                             key="firms.cred")
    st.sidebar.subheader("Fiscal policy")
    vat = st.sidebar.slider("VAT change (pp)", -5.0, 10.0, float(f["vat_change"]), 0.5,
                            key="firms.vat")
    return {"money": money}, [f"fields.money_growth={number(money, 0)}",
                              f"fields.credibility={number(cred)}",
                              f"fields.vat_change={number(vat, 1)}"]


def taxpayer_levers(spec):
    f = spec["fields"]
    st.sidebar.subheader("Enforcement")
    audit = st.sidebar.slider("Audit probability", 0.0, 0.3, float(f["audit_prob"]), 0.01,
                              key="taxpayers.audit")
    penalty = st.sidebar.slider("Penalty (periods)", 0, 20, int(f["penalty"]), 1,
                                key="taxpayers.penalty",
                                help="Periods of forced honesty (Zaklan's k)")
    st.sidebar.subheader("Tax")
    rate = st.sidebar.slider("Tax rate (%)", 10.0, 60.0, float(f["tax_rate"]), 1.0,
                             key="taxpayers.rate")
    return {"audit": audit}, [f"fields.audit_prob={number(audit)}", f"fields.penalty={int(penalty)}",
                              f"fields.tax_rate={number(rate, 0)}"]


LEVERS = {"banks": bank_levers, "firms": firm_levers, "taxpayers": taxpayer_levers}


def join_names(names):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def extreme(preset, values):
    """Compliance is bad when it is low. Everything else is bad when it is high."""
    return min(values) if preset == "taxpayers" else max(values)


def headline(preset, levers, gamma, r, cf):
    """One sentence rewritten from the numbers on every run."""
    key = r["headline"]
    y = r["series"][key]
    peak = extreme(preset, y)
    base = extreme(preset, r["baseline"]["series"][key])
    if preset == "banks":
        labels = r["labels"]
        seed = labels[levers["seed"]]
        if gamma == 0:
            return f"With Γ = 0 every term commutes: {seed} stays failed and no other bank moves."
        if levers["bail"] and cf:
            names = join_names([labels[i] for i in levers["bail"]])
            return (f"Bailing out {names} holds peak insolvency to **{peak:.0%}**, "
                    f"down from {max(cf['series'][key]):.0%}.")
        ratio = peak / max(base, 1e-9)
        tail = f", {ratio:.1f}× the background rate." if ratio > 1.25 else ", barely above background noise."
        return f"When {seed} fails, up to **{peak:.0%}** of the banking system is insolvent{tail}"
    if preset == "firms":
        if gamma == 0:
            return "With Γ = 0 nothing moves: firms hold their prices whatever the central bank does."
        gap, money = peak - base, f"{levers['money']:.0f}%"
        if gap > 0.15:
            return f"At {money} money growth, expectations de-anchor: up to **{peak:.0%}** of firms raise prices."
        if gap > 0.04:
            return f"At {money} money growth, up to **{peak:.0%}** of firms raise prices, {gap * 100:.0f} points above target."
        return f"At {money} money growth, expectations stay anchored: at most **{peak:.0%}** of firms raise prices."
    if gamma == 0:
        return "With Γ = 0 nothing moves: the evaders stay evaders and everyone else stays honest."
    tail = " as the evaders pull their neighbours along." if peak < y[0] - 0.03 else "; the evaders stay contained."
    return f"With a {levers['audit']:.0%} audit rate, compliance bottoms out at **{peak:.0%}**{tail}"


def points(x):
    return f"{x * 100:+.0f} pts"


def show_stats(preset, levers, r, cf):
    key = r["headline"]
    y = np.array(r["series"][key])
    base = np.array(r["baseline"]["series"][key])
    low = preset == "taxpayers"
    k = int(np.argmin(y) if low else np.argmax(y))
    at = f"at t = {r['times'][k]:.2f}"
    cols = st.columns(4)
    if preset == "banks":
        P = np.array(r["per_agent"]["p_one"])
        B = np.array(r["baseline"]["per_agent"]["p_one"])
        excess = (P - B).max(axis=0)
        excess[levers["seed"]] = -np.inf
        worst = int(np.argmax(excess))
        cols[0].metric("Peak insolvent", f"{y.max():.0%}", help=at)
        cols[1].metric("Contagion", points((y - base).max()), help="Above the no-shock background")
        cols[2].metric("Most exposed", r["labels"][worst],
                       help=f"Peak {P[:, worst].max():.0%} vs {B[:, worst].max():.0%} background")
        effect = points(y.max() - max(cf["series"][key])) if cf else "none"
        cols[3].metric("Bailout effect", effect, help="Against the same shock with no bailout")
    elif preset == "firms":
        half = int(np.argmax(y >= y.max() / 2))
        cols[0].metric("Peak raising prices", f"{y.max():.0%}", help=at)
        cols[1].metric("vs on-target economy", points(y.max() - base.max()),
                       help="Peak share, against money growth at target")
        cols[2].metric("Time to half peak", f"{r['times'][half]:.2f} / J", help="Speed of propagation")
        cols[3].metric("Neighbour agreement", f"{r['series']['synchronization'][k]:.2f}",
                       help="⟨ZᵢZⱼ⟩ at the peak")
    else:
        cols[0].metric("Lowest compliance", f"{y.min():.0%}", help=at)
        cols[1].metric("vs no evaders", points(y.min() - base.min()),
                       help="Lowest compliance, against a lattice with no evaders")
        cols[2].metric("Starting compliance", f"{y[0]:.0%}")
        cols[3].metric("Neighbour agreement", f"{r['series']['synchronization'][k]:.2f}",
                       help="⟨ZᵢZⱼ⟩ at the lowest point")


def show_model(preset, r):
    s = r["summary"]
    g = r["graph"]
    st.latex(r"H=-\sum_{(i,j)}J_{ij}Z_iZ_j-\sum_i h_iZ_i-\sum_i\Gamma_iX_i")
    st.markdown("\n".join(f"- **{term}**: {meaning}" for term, meaning in SCENARIOS[preset]["mapping"]))
    cols = st.columns(4)
    cols[0].metric("Qubits", s["n"])
    cols[1].metric("Exact memory", human_bytes(s["statevector_bytes"]), help="16 · 2ⁿ bytes")
    cols[2].metric("Two-qubit gates per step", s["cx_per_step"],
                   help=f"{s['rzz_per_step']} RZZ at 2 CX each, order {s['order']}, before routing")
    if "trotter_max_error" in r:
        cols[3].metric("Max error vs exact", f"{r['trotter_max_error']:.1e}",
                       help="Trotter circuit against the exact matrix exponential")
    left, right = st.columns([1.3, 1])
    rows = ["| Agent | h | Γ | Starts as | Hops from seed |", "|---|---:|---:|---|---:|"]
    for i in range(g["n"]):
        start = r["states"]["1"] if i in g["init_ones"] else r["states"]["0"]
        rows.append(f"| {r['labels'][i]} | {g['h'][i]:+.3f} | {g['gamma'][i]:.2f} | {start} "
                    f"| {g['distance_from_seed'][i]} |")
    left.markdown("\n".join(rows))
    rows = ["| Link | J |", "|---|---:|"]
    rows += [f"| {r['labels'][i]} – {r['labels'][j]} | {J:.3f} |" for i, j, J in g["edges"]]
    right.markdown("\n".join(rows))
    st.markdown("**Sources**")
    st.markdown("\n".join(f"- *{k}*: {v}" for k, v in r["sources"].items()))


def show_spec_editor(preset, r):
    st.markdown("The YAML behind the current levers. Edit it and press **Validate and run**. "
                "The validator lists every problem before anything expensive starts.")
    text = st.text_area("Spec", yaml.safe_dump(r["spec"], sort_keys=False, allow_unicode=True),
                        height=420, label_visibility="collapsed", key=f"spec.{preset}")
    if not st.button("Validate and run", type="primary", key=f"run.{preset}"):
        return
    try:
        spec = yaml.safe_load(text)
    except yaml.YAMLError as e:
        st.error(f"Not valid YAML: {e}")
        return
    if not isinstance(spec, dict):
        st.error("The spec must be a mapping of key: value pairs.")
        return
    try:
        too_big = public_limit_errors(spec)
        if too_big:
            st.error("\n\n".join(too_big))
            return
        custom = run_spec(spec)
    except SpecError as e:
        st.error(f"```\n{e}\n```")
        return
    key = custom["headline"]
    st.success(f"Valid. Compiled {custom['summary']['n']} qubits. "
               f"{custom['headline_label']} reaches {max(custom['series'][key]):.0%}.")
    st.plotly_chart(charts.headline_chart(custom), width="stretch")


def reset_levers(preset):
    for key in list(st.session_state):
        if key.startswith((f"{preset}.", f"gamma.{preset}", f"spec.{preset}")):
            del st.session_state[key]


def main():
    st.set_page_config(page_title="QEcon", layout="wide")
    st.sidebar.title("QEcon")
    st.sidebar.caption("Economic network → Ising Hamiltonian → Trotter circuit")
    preset = st.sidebar.radio("Scenario", list(SCENARIOS), key="scenario",
                              format_func=lambda p: SCENARIOS[p]["tab"])
    spec = base_spec(preset)
    levers, overrides = LEVERS[preset](spec)
    st.sidebar.subheader("Uncertainty (the quantum term)")
    gamma = st.sidebar.slider("Transverse field Γ", 0.0, 1.5, float(spec["uncertainty"]["gamma"]),
                              0.05, key=f"gamma.{preset}",
                              help="The only non-commuting term. At 0, nothing can move.")
    gamma = round(gamma, 2)
    overrides.append(f"uncertainty.gamma={number(gamma)}")
    st.sidebar.button("Reset levers", on_click=reset_levers, args=(preset,))

    try:
        with st.spinner("Compiling the Hamiltonian and simulating circuits…"):
            response = api_run({"preset": preset, "overrides": overrides, "exact": True})
    except SpecError as e:
        st.error(f"```\n{e}\n```")
        st.stop()

    r, cf = response["result"], response["counterfactual"]
    scenario = SCENARIOS[preset]
    st.caption(scenario["title"].upper())
    st.markdown(f"### {headline(preset, levers, gamma, r, cf)}")
    st.markdown(scenario["dek"])
    show_stats(preset, levers, r, cf)
    for warning in r["warnings"]:
        st.warning(warning)

    dynamics, cone, model, editor, about = st.tabs(
        ["Dynamics", "Light-cone", "Model", "Spec", "What we claim"])
    with dynamics:
        left, right = st.columns([1.05, 1])
        with left:
            st.plotly_chart(charts.headline_chart(r, cf, response["counterfactual_label"],
                                                  response["hardware"], scenario["baseline"]),
                            width="stretch")
        with right:
            st.plotly_chart(charts.network_chart(r), width="stretch")
        notes = []
        if "trotter_max_error" in r:
            notes.append(f"Trotter circuit vs exact evolution: max error {r['trotter_max_error']:.1e}.")
        notes += [f"Diamonds are {d.get('backend')}: {d.get('kind')}." for d in response["hardware"]]
        st.caption(" ".join(notes))
    with cone:
        left, right = st.columns(2)
        other = cf if cf else r["baseline"]
        name = response["counterfactual_label"] if cf else scenario["baseline"]
        with left:
            st.plotly_chart(charts.heatmap(r, "Current policy"), width="stretch")
        with right:
            st.plotly_chart(charts.heatmap({**r, "per_agent": other["per_agent"]}, f"Compared with: {name}"),
                            width="stretch")
        st.caption("Rows are sorted by hops from the seeded agent. Γ flips agents on their own, so "
                   "contagion is the difference between the two panels. Coherent dynamics is "
                   "reversible, so a cascade can partly un-spread.")
    with model:
        show_model(preset, r)
    with editor:
        show_spec_editor(preset, r)
    with about:
        st.markdown("""
**We claim** a working, validated compiler from an economic spec to a quantum circuit. For this
coherent model, exact classical simulation needs 16·2ⁿ bytes, while circuit size grows linearly
with the number of interactions.

**We do not claim** better economic forecasts, a speedup over classical econophysics (those
models are classical Monte Carlo), or that people or economies are physically quantum.

- Scales such as κ, β and Γ are dimensionless calibration knobs, not estimated from data.
- Bank data is illustrative, not real institutions.
- Real exposure is directed. A Hermitian ZZ coupling is symmetric, so direction is lost.
- Entanglement here is a correlation measure of the model, not a claim about real agents.
- Tensor networks can go well beyond exact state vectors when entanglement stays low.
""")


main()
