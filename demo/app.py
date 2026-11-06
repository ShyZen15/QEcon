"""QEcon live demo (Streamlit).

    streamlit run demo/app.py

Everything runs on the local statevector simulator, so it cannot fail on stage.
Hardware points (results/hardware/*.json, made by `python -m backends.hardware`) are
overlaid when they exist and silently skipped when they don't.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# pandas is optional here. On some Windows laptops Application Control blocks one of
# pandas' DLLs, leaving a half-imported module that crashes plotly on rerun. Try once;
# if it fails, mark it missing so every later import raises a clean ImportError.
try:
    import pandas  # noqa: F401
except Exception:  # noqa: BLE001
    for _m in [m for m in sys.modules if m == "pandas" or m.startswith("pandas.")]:
        del sys.modules[_m]
    sys.modules["pandas"] = None

import numpy as np  # noqa: E402
import plotly.graph_objects  # noqa: E402,F401
import streamlit as st  # noqa: E402
import yaml  # noqa: E402

from demo import charts  # noqa: E402
from qecon.api import run_spec  # noqa: E402
from qecon.spec import SpecError, load_spec  # noqa: E402

SPEC_FILES = {
    "Banks: interbank contagion": "specs/banks.yaml",
    "Firms: inflation expectations": "specs/firms.yaml",
    "Taxpayers: tax compliance": "specs/taxpayers.yaml",
}
HW_DIR = os.path.join(ROOT, "results", "hardware")

st.set_page_config(page_title="QEcon: economics as a quantum Hamiltonian", layout="wide")
st.markdown(
    "<style>div.block-container{padding-top:1.6rem;} "
    "[data-testid='stMetricValue']{font-size:1.5rem;}</style>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------------------
def spec_hash(spec):
    clean = {k: v for k, v in spec.items() if not k.startswith("_")}
    return hashlib.sha1(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:12]


@st.cache_data(show_spinner=False, max_entries=256)
def simulate(spec_json, baseline, exact):
    return run_spec(json.loads(spec_json), baseline=baseline, exact=exact)


def run(spec, baseline=False, exact=False):
    return simulate(json.dumps(spec, sort_keys=True), baseline, exact)


@st.cache_data(show_spinner=False)
def base_spec(path):
    return load_spec(os.path.join(ROOT, path))


def hardware_runs(result, h):
    """Hardware / noisy-simulator JSONs whose spec hash matches the current parameters."""
    if not os.path.isdir(HW_DIR):
        return [], []
    match, other = [], []
    for f in sorted(os.listdir(HW_DIR)):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(HW_DIR, f), encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("preset") != result["preset"] or "series" not in d:
            continue
        (match if d.get("spec_hash") == h else other).append(d)
    return match, other


# ---------------------------------------------------------------------------------------
st.sidebar.title("QEcon")
st.sidebar.caption("Economic agents → transverse-field Ising Hamiltonian → Trotter circuit")
choice = st.sidebar.selectbox("Economy", list(SPEC_FILES))
spec = json.loads(json.dumps(base_spec(SPEC_FILES[choice])))   # deep copy
spec.pop("_path", None)
preset = spec["preset"]
f = spec["fields"]
compare = None        # (label, spec) for a side-by-side counterfactual

if preset == "banks":
    labels = spec["agents"]["labels"]
    st.sidebar.subheader("Shock")
    seed = st.sidebar.selectbox("Bank that fails", labels, index=f["shock"]["nodes"][0])
    k = labels.index(seed)
    spec["initial"]["ones"] = [k]
    f["shock"]["nodes"] = [k]
    st.sidebar.subheader("Policy")
    bail = st.sidebar.multiselect("Bail out", [x for x in labels if x != seed],
                                  help="Adds a solvency field h += strength on these banks")
    f["bailout"]["nodes"] = [labels.index(x) for x in bail]
    f["bailout"]["strength"] = st.sidebar.slider("Bailout size (field strength)", 0.0, 4.0,
                                                 float(f["bailout"]["strength"]), 0.25)
    f["kappa"] = st.sidebar.slider("Capital sensitivity κ (h per pp of CET1 above 7%)",
                                   0.0, 0.3, float(f["kappa"]), 0.01)
    if bail:
        no_bail = json.loads(json.dumps(spec))
        no_bail["fields"]["bailout"]["nodes"] = []
        compare = ("Without the bailout", no_bail)

elif preset == "firms":
    st.sidebar.subheader("Monetary policy")
    f["money_growth"] = st.sidebar.slider("Money-supply growth (% / yr)", 0.0, 25.0,
                                          float(f["money_growth"]), 1.0)
    f["credibility"] = st.sidebar.slider("Central-bank credibility", 0.0, 1.0,
                                         float(f["credibility"]), 0.05)
    st.sidebar.subheader("Fiscal policy")
    f["vat_change"] = st.sidebar.slider("VAT / sales-tax change (pp)", -5.0, 10.0,
                                        float(f["vat_change"]), 0.5)
    on_target = json.loads(json.dumps(spec))
    on_target["fields"]["money_growth"] = f["target"]
    on_target["fields"]["vat_change"] = 0.0
    if f["money_growth"] != f["target"] or f["vat_change"] != 0:
        compare = ("Money growth on target, no tax change", on_target)

else:  # taxpayers
    st.sidebar.subheader("Enforcement")
    f["audit_prob"] = st.sidebar.slider("Audit probability", 0.0, 0.30, float(f["audit_prob"]), 0.01)
    f["penalty"] = st.sidebar.slider("Penalty (periods of forced honesty)", 0, 20, int(f["penalty"]))
    st.sidebar.subheader("Tax")
    f["tax_rate"] = st.sidebar.slider("Tax rate (%)", 10.0, 60.0, float(f["tax_rate"]), 1.0)

st.sidebar.subheader("Uncertainty")
spec["uncertainty"]["gamma"] = st.sidebar.slider(
    "Γ (transverse field: indecision)", 0.0, 1.5, float(spec["uncertainty"]["gamma"]), 0.05,
    help="The only non-commuting term. Set it to 0 and nothing moves.")
st.sidebar.subheader("Show")
show_base = st.sidebar.checkbox("No-shock baseline", value=preset == "banks",
                                help="Same economy without the shock: separates contagion from Γ-noise")
show_exact = st.sidebar.checkbox("Exact evolution (matrix exponential)", value=True)
show_hw = st.sidebar.checkbox("Hardware points (if run)", value=True)

# ---------------------------------------------------------------------------------------
try:
    with st.spinner("Compiling Hamiltonian and simulating circuits…"):
        r = run(spec, baseline=show_base, exact=show_exact)
        rc = run(compare[1]) if compare else None
except SpecError as e:
    st.error(f"Spec rejected by the validator:\n\n```\n{e}\n```")
    st.stop()

h = spec_hash(r["spec"])   # validated spec (defaults filled), same as backends/hardware.py
hw_match, hw_other = hardware_runs(r, h) if show_hw else ([], [])
s = r["summary"]
key = r["headline"]
y = np.array(r["series"][key])

st.title({"banks": "Interbank contagion", "firms": "Inflation expectations",
          "taxpayers": "Tax compliance"}[preset])
st.caption(f"|0⟩ = {r['states']['0']}, |1⟩ = {r['states']['1']}.  "
           "H = −Σ Jᵢⱼ ZᵢZⱼ − Σ hᵢ Zᵢ − Σ Γᵢ Xᵢ.  "
           f"Simulated as {s['trotter_steps_at_t_max']} second-order Trotter steps on a "
           "statevector simulator.")

m = st.columns(5)
m[0].metric("Agents (qubits)", s["n"])
m[1].metric("Interactions (ZZ edges)", s["edges"])
PEAK = {"banks": "Peak share insolvent", "firms": "Peak share raising prices",
        "taxpayers": "Peak compliance"}
m[2].metric(PEAK[preset], f"{y.max():.0%}",
            delta=(f"{y.max() - max(rc['series'][key]):+.0%} vs counterfactual" if rc else None),
            delta_color="inverse" if preset != "taxpayers" else "normal")
m[3].metric("Exact-simulation memory", charts.human_bytes(16 * 2 ** s["n"]),
            help="16·2ⁿ bytes for the full statevector. Doubles with every agent.")
m[4].metric("2-qubit gates / Trotter step", f"~{s['cx_per_step']}",
            help=f"{s['rzz_per_step']} RZZ gates (2 CX each), before routing. Linear in edges.")

for w in r["warnings"]:
    st.warning(w)

tab_live, tab_cone, tab_model, tab_spec = st.tabs(
    ["Dynamics", "Light-cone", "The Hamiltonian", "Spec & validator"])

with tab_live:
    c1, c2 = st.columns([1.05, 1])
    with c1:
        st.plotly_chart(charts.headline_chart(r, rc, compare[0] if compare else None,
                                              hw_match), width="stretch")
        if show_hw and not hw_match and hw_other:
            st.caption("Hardware points exist for this economy at its default settings: "
                       "reset the sliders to see them.")
    with c2:
        st.plotly_chart(charts.network_chart(r), width="stretch")
    if "excess" in r:
        ex = np.array(r["excess"]["series"][key])
        st.caption(f"Excess over the no-shock baseline (contagion, not Γ-noise): "
                   f"peak {ex.max():+.0%}, time-average {ex.mean():+.0%}.")
    if "trotter_max_error" in r:
        st.caption(f"Trotter circuit vs exact matrix exponential: max error "
                   f"{r['trotter_max_error']:.1e}.")

with tab_cone:
    if rc is not None:
        a, b = st.columns(2)
        with a:
            st.plotly_chart(charts.heatmap(r, "With current policy"), width="stretch")
        with b:
            st.plotly_chart(charts.heatmap(rc, compare[0]), width="stretch")
    else:
        st.plotly_chart(charts.heatmap(r, "P(state 1) per agent"), width="stretch")
    st.caption("Rows sorted by graph distance from the seeded agent (d = hops). "
               "Coherent dynamics is reversible, so a cascade can partially un-spread.")

with tab_model:
    st.markdown("**Every economic knob is one term of one Hamiltonian.**")
    st.latex(r"H=-\sum_{(i,j)}J_{ij}Z_iZ_j-\sum_i h_iZ_i-\sum_i\Gamma_iX_i")
    g = r["graph"]
    a, b = st.columns([1.3, 1])
    with a:
        rows = ["| agent | h_i (field) | Γ_i | starts in | hops from seed |",
                "|---|---:|---:|---|---:|"]
        for i in range(g["n"]):
            start = r["states"]["1"] if i in g["init_ones"] else r["states"]["0"]
            rows.append(f"| {r['labels'][i]} | {g['h'][i]:+.3f} | {g['gamma'][i]:.2f} | "
                        f"{start} | {g['distance_from_seed'][i]} |")
        st.markdown(chr(10).join(rows))
    with b:
        rows = ["| i | j | J_ij |", "|---|---|---:|"]
        rows += [f"| {r['labels'][i]} | {r['labels'][j]} | {J:.3f} |" for i, j, J in g["edges"]]
        st.markdown(chr(10).join(rows))
    st.markdown("**Sources**")
    for k_, v in r["sources"].items():
        st.markdown(f"- *{k_}*: {v}")

with tab_spec:
    st.markdown("The YAML the sliders are editing. Change anything and press **Run spec**. "
                "The validator rejects bad specs before anything expensive runs.")
    text = st.text_area("Spec", yaml.safe_dump(spec, sort_keys=False, allow_unicode=True),
                        height=420, label_visibility="collapsed")
    if st.button("Run spec", type="primary"):
        try:
            custom = yaml.safe_load(text)
            rr = run(custom)
            st.success(f"Valid. Peak {rr['headline_label'].lower()}: "
                       f"{max(rr['series'][rr['headline']]):.0%}")
            st.plotly_chart(charts.headline_chart(rr, None, None, []), width="stretch")
        except SpecError as e:
            st.error(f"```\n{e}\n```")
        except yaml.YAMLError as e:
            st.error(f"Not valid YAML: {e}")
