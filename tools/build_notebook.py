"""Compiles the whole project into one self-contained notebook, QEcon_submission.ipynb.

    python tools/build_notebook.py          # rebuild from the repo and run it
    python tools/build_notebook.py --no-run # rebuild without running

Every module is embedded unchanged as a %%writefile cell, so a reader needs only the
notebook, and the code it runs is the code in this repo. tests/test_notebook.py fails if
the notebook and the repo ever drift apart.
"""
import base64
import os
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "QEcon_submission.ipynb"
BUILD = "qecon_src"
REPO_URL = "https://github.com/ShyZen15/QEcon"
APP_URL = "https://qecon-q.streamlit.app"

HARDWARE_RESULT = "results/hardware/banks_core_periphery_8_FakeBoston.json"

ENGINE = ["core/__init__.py", "core/engine.py"]
SPECS = ["specs/banks.yaml", "specs/firms.yaml", "specs/taxpayers.yaml"]
PLUGINS = ["plugins/__init__.py", "plugins/common.py", "plugins/banks.py", "plugins/firms.py",
           "plugins/taxpayers.py"]
QECON = ["qecon/__init__.py", "qecon/spec.py", "qecon/api.py", "qecon/plots.py", "qecon/__main__.py"]
VALIDATION = ["validation/__init__.py", "validation/systems.py", "validation/reference.py",
              "validation/glauber.py", "validation/plotting.py", "validation/fig1_trotter.py",
              "validation/fig2_memory_wall.py", "validation/fig5_observable_error.py",
              "validation/fig4_glauber.py", "validation/fig3_entropy.py"]
HARDWARE = ["backends/__init__.py", "backends/hardware.py", HARDWARE_RESULT]
FRONTEND = ["demo/__init__.py", "demo/server.py", "demo/charts.py", "demo/streamlit_app.py",
            "demo/requirements.txt", ".streamlit/config.toml"]
TESTS = ["conftest.py", "validation/test_engine.py", "tests/test_plugins.py",
         "tests/test_spec_guards.py", "tests/test_integration.py"]
EMBEDDED = ENGINE + SPECS + PLUGINS + QECON + VALIDATION + HARDWARE + FRONTEND + TESTS


def md(text):
    return new_markdown_cell(text.strip())


def code(text):
    return new_code_cell(text.strip())


def hidden(cell, tag):
    cell.metadata["jupyter"] = {"source_hidden": True}
    cell.metadata["tags"] = [tag]
    return cell


def embed(paths):
    """One collapsed %%writefile cell per file, with the file's exact text."""
    cells = []
    for path in paths:
        text = (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")
        if text.strip():    # %%writefile rejects an empty body. The setup cell makes those.
            cells.append(hidden(new_code_cell(f"%%writefile {BUILD}/{path}\n{text}"), "source"))
    return cells


def citations():
    text = (ROOT / "CITATIONS.md").read_text(encoding="utf-8")
    return text[text.index("## Used directly"):].replace("## ", "### ")


INTRO = f"""
# QEcon: economic policy as a quantum Hamiltonian

**Team Quantum Larpers:** Snigdha (engine) · Shiven (validation) · Isha (plugins and spec language) · Arsh (frontend and hardware)

**Qiskit Fall Fest 2026** · Code: [{REPO_URL}]({REPO_URL}){f" · Live app: [{APP_URL}]({APP_URL})" if APP_URL else ""}

QEcon is a compiler. It takes a plain description of an economic network (banks, firms or
taxpayers) and turns it into a transverse-field Ising Hamiltonian, then into a Qiskit Trotter
circuit, then back into economic numbers:

$$H = -\\sum_{{(i,j)}} J_{{ij}} Z_i Z_j \\;-\\; \\sum_i h_i Z_i \\;-\\; \\sum_i \\Gamma_i X_i$$

| Term | Economic meaning |
|---|---|
| $J_{{ij}} Z_i Z_j$ | Interaction: exposure between banks, price imitation, social influence |
| $h_i Z_i$ | Policy and fundamentals: capital buffers, money growth, audits, bailouts |
| $\\Gamma_i X_i$ | Uncertainty. The only non-commuting term, so the only quantum ingredient |

Each agent is a qubit: $|0\\rangle$ is solvent, holding prices or compliant, and $|1\\rangle$ is
insolvent, raising prices or evading.

### Results

Every number below is recomputed when this notebook runs, and [Part 3](#p3) stops if any stops being true.

| Scenario | Result |
|---|---|
| **Contagion** (8 banks) | When Core-B fails, peak insolvency reaches 45%, against 22% with no shock. Bailing out Core-A cuts its own peak failure from 47% to 10%. |
| **Inflation** (12 firms) | Peak share of firms raising prices goes from 5.5% at 2% money growth to 54% at 20%. |
| **Compliance** (12 taxpayers) | A cluster of 3 evaders pulls compliance down to 70%. Raising audits from 5% to 20% lifts that floor to 74%. |
| **Validation** | Circuits match an independent NumPy model. Trotter slopes are −2.03 and −4.07 (theory: −2 and −4). With $\\Gamma = 0$ the error is zero to machine precision. |

### What we do not claim

We do **not** claim better economic forecasts, a speedup over classical econophysics, or that
people or economies are physically quantum. The claim is narrow: this is a working, validated
compiler, and for this coherent model exact classical simulation needs $16 \\cdot 2^n$ bytes
while circuit size grows linearly with the number of interactions. [Part 8](#p8) has the full list.

### Contents

1. [The engine](#p1): Hamiltonian to circuit
2. [The spec language](#p2): YAML to Hamiltonian, with a validator
3. [Three economies](#p3): contagion, inflation, compliance
4. [Validation](#p4): how we know it is right
5. [Hardware readiness](#p5)
6. [The frontend](#p6)
7. [The full test suite](#p7)
8. [Limits and references](#p8)

**To run:** use Run All. It needs only this file. It takes about two minutes, or about six if the
first cell has to install packages. The project's source is written to a `{BUILD}/` folder beside
the notebook. Source cells are collapsed, so expand any of them to read the code.
"""

SETUP = f'''
import importlib.util
import subprocess
import sys

REQUIRED = {{"qiskit": "qiskit==2.6.2", "qiskit_aer": "qiskit-aer==0.18.2",
            "qiskit_ibm_runtime": "qiskit-ibm-runtime==0.51.0", "scipy": "scipy",
            "networkx": "networkx", "yaml": "pyyaml", "matplotlib": "matplotlib",
            "plotly": "plotly", "pytest": "pytest"}}
missing = [pin for module, pin in REQUIRED.items() if importlib.util.find_spec(module) is None]
if missing:
    print("Installing:", ", ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])

import json
import os
from pathlib import Path

import numpy as np
import qiskit
from IPython.display import HTML, Image, Markdown, display

BUILD = Path("{BUILD}").resolve()
for folder in ("core", "specs", "plugins", "qecon", "validation", "backends", "results/hardware",
               "demo", ".streamlit", "tests", "out"):
    (BUILD / folder).mkdir(parents=True, exist_ok=True)
for package in ("core", "validation", "backends", "demo"):
    (BUILD / package / "__init__.py").touch()
sys.path.insert(0, str(BUILD))


def spec_path(name):
    return str(BUILD / "specs" / f"{{name}}.yaml")


def show(path, width=900):
    display(Image(filename=str(path), width=width))


print("Qiskit", qiskit.__version__, "| source folder:", BUILD)
'''

ENGINE_DEMO = '''
from qiskit.quantum_info import Statevector
from core.engine import compile_ising, evolve, exact_state

# Three agents in a triangle, with a different field on each. Agent 0 starts in |1>.
edges = {(0, 1): 1.0, (1, 2): 0.8, (0, 2): 0.6}
H = compile_ising(3, edges, h=[0.2, -0.1, 0.3], gamma=[0.5, 0.5, 0.5])
print("Hamiltonian:", H, "\\n")

circuit = evolve(H, t=1.0, steps=1, init_ones=(0,), order=1)
print(circuit.draw("text", fold=110), "\\n")

exact = exact_state(H, 1.0, (0,))
for steps in (1, 4, 16, 64):
    psi = Statevector(evolve(H, 1.0, steps, (0,), 1)).data
    print(f"{steps:3d} Trotter steps: infidelity vs exact = {1 - abs(np.vdot(exact, psi)) ** 2:.2e}")
'''

VALIDATOR_DEMO = '''
from qecon.api import prepare, run_spec
from qecon.spec import SpecError, load_spec

plugin, spec, warnings = prepare(spec_path("banks"))
n, edges, h, gamma = plugin.system()
print(f"{spec['name']}: {n} qubits, {len(edges)} ZZ terms")
print("Strongest links:", [(plugin.labels()[i], plugin.labels()[j], round(J, 2))
                           for (i, j), J in sorted(edges.items(), key=lambda e: -e[1])[:3]], "\\n")

bad = load_spec(spec_path("banks"))
bad["_path"] = "specs/banks.yaml"
bad["network"]["holdings"][0] = [0, 99, 0.15]    # a bank that doesn't exist
bad["fields"]["kapa"] = 0.5                      # a typo
bad["initial"]["ones"] = [1, 1]                  # the same bank twice
bad["uncertainty"]["gamma"] = -1                 # a negative field
try:
    run_spec(bad)
except SpecError as error:
    print(error)
'''

SCENARIOS = '''
from qecon.plots import plot_compare, plot_lightcone_pair

OUT = BUILD / "out"
banks = {
    "no shock": run_spec(spec_path("banks"), overrides=["initial.ones=[]", "fields.shock.nodes=[]"]),
    "Core-B fails": run_spec(spec_path("banks"), exact=True),
    "+ bail out Core-A": run_spec(spec_path("banks"), overrides=["fields.bailout.nodes=[0]"]),
}
plot_compare(list(banks.values()), list(banks), OUT / "banks.png",
             "Interbank contagion: Core-B fails (8 banks, EGJ cross-holdings)")
plot_lightcone_pair(banks["Core-B fails"], banks["+ bail out Core-A"], OUT / "banks_cone.png",
                    "Core-B fails: P(insolvent) by distance from Core-B",
                    "Same shock, Core-A bailed out")
show(OUT / "banks.png")
show(OUT / "banks_cone.png")
'''

FIRMS = '''
money = [2, 8, 14, 20]
firms = [run_spec(spec_path("firms"), overrides=[f"fields.money_growth={m}"], exact=True) for m in money]
plot_compare(firms, [f"money growth {m}%" for m in money], OUT / "firms.png",
             "Price-setting firms on a 4x3 supply grid: monetary shock")
show(OUT / "firms.png")
'''

TAXPAYERS = '''
audits = [0.02, 0.05, 0.20]
taxpayers = [run_spec(spec_path("taxpayers"), overrides=[f"fields.audit_prob={p}"], exact=True) for p in audits]
plot_compare(taxpayers, [f"audit probability {p:.0%}" for p in audits], OUT / "taxpayers.png",
             "Tax compliance (coherent Zaklan model): evader cluster on a 4x3 lattice")
show(OUT / "taxpayers.png")
'''

CLAIMS = '''
def peak(result):
    return max(result["series"][result["headline"]])


def floor(result):
    return min(result["series"][result["headline"]])


def agent_peak(result, i):
    return float(np.array(result["per_agent"]["p_one"])[:, i].max())


rows = [
    ("Peak insolvency when Core-B fails", peak(banks["Core-B fails"]), 0.45),
    ("Peak insolvency with no shock", peak(banks["no shock"]), 0.22),
    ("Core-A peak failure, no bailout", agent_peak(banks["Core-B fails"], 0), 0.47),
    ("Core-A peak failure, bailed out", agent_peak(banks["+ bail out Core-A"], 0), 0.10),
    ("Peak firms raising, 2% money growth", peak(firms[0]), 0.055),
    ("Peak firms raising, 20% money growth", peak(firms[3]), 0.54),
    ("Lowest compliance, 5% audits", floor(taxpayers[1]), 0.70),
    ("Lowest compliance, 20% audits", floor(taxpayers[2]), 0.74),
]
table = ["| Claim | Computed now | Stated above |", "|---|---:|---:|"]
for name, value, stated in rows:
    assert abs(value - stated) < 0.0101, (name, value, stated)
    table.append(f"| {name} | {value:.1%} | {stated * 100:g}% |")
errors = [r["trotter_max_error"] for r in [banks["Core-B fails"], *firms, *taxpayers]]
table.append(f"| Largest Trotter error vs exact, all runs above | {max(errors):.1e} | below 1e-2 |")
assert max(errors) < 1e-2
display(Markdown("\\n".join(table)))
'''

VALIDATION_INTRO = '''
from validation import reference
from validation.systems import standard_system

system = standard_system()
ours = compile_ising(system.n, system.edges, system.h, system.gamma).to_matrix(sparse=True).tocsc()
independent = reference.hamiltonian(system.n, system.edges, system.h, system.gamma)
print("Engine vs independent Hamiltonian, largest difference:", abs(ours - independent).max())

for name in ("banks", "firms", "taxpayers"):
    plugin, _, _ = prepare(spec_path(name))
    n, edges, h, gamma = plugin.system()
    gap = abs(plugin.hamiltonian().to_matrix(sparse=True) - reference.hamiltonian(n, edges, h, gamma)).max()
    assert gap < 1e-12
    print(f"{name:10s} preset vs independent Hamiltonian, largest difference: {gap:.1e}")
'''


def figure(module):
    return f'''
from validation import {module}

{module}.main()
show(BUILD / "validation" / "figures" / "{module}.png")
'''


HARDWARE_DEMO = f'''
from backends.hardware import main as hardware, report

hardware(["plan", spec_path("banks"), "--device", "FakeBoston"])
print()
report(json.loads((BUILD / "{HARDWARE_RESULT}").read_text()))
'''

FRONTEND_DEMO = '''
from demo import charts
from demo.server import api_run

# The default levers, sent through the same function the app calls.
levers = ["initial.ones=[1]", "fields.shock.nodes=[1]", "fields.bailout.nodes=[0]",
          "fields.bailout.strength=2.0", "fields.kappa=0.05", "uncertainty.gamma=0.6"]
response = api_run({"preset": "banks", "overrides": levers})
print("Counterfactual:", response["counterfactual_label"])
figure = charts.network_chart(response["result"])
display(HTML(figure.to_html(include_plotlyjs="cdn", full_html=False)))
'''

TESTS_RUN = '''
run = subprocess.run([sys.executable, "-m", "pytest", "validation", "tests", "-q", "-k", "not server",
                      "--color=no", "-p", "no:cacheprovider"], cwd=BUILD, capture_output=True, text=True)
print("\\n".join(run.stdout.strip().splitlines()[-6:]))
assert run.returncode == 0
'''

LIMITS = """
<a id="p8"></a>
## Part 8: Limits and references

### What we do not claim

- **No better forecasts.** This is a stylised model, not one fitted to economic data.
- **No speedup over classical econophysics.** Models such as Zaklan's are classical Monte Carlo
  and already scale to millions of agents. Ours is a different model, not a faster version.
- **No claim that economies are quantum.** The Hilbert-space maths is a modelling choice.
  Quantum cognition has contested single-agent evidence, and inter-agent entanglement has no
  empirical support we know of. Entanglement here is a correlation measure of the model.
- **No claim to beat all classical simulation.** The memory wall is about exact state vectors.
  Tensor networks reproduced IBM's 127-qubit kicked-Ising experiment, and they go much further
  when entanglement stays low. One-dimensional chains are exactly solvable, which is why our
  presets use 2D grids and networks with a longitudinal field.

### Modelling limits

- Scales such as $\\kappa$, $\\beta$ and $\\Gamma$ are dimensionless calibration knobs chosen by
  exact-evolution scans. The literature fixes the structure and the direction of each policy,
  not these sizes.
- Bank data is illustrative, not real institutions.
- Real exposure is directed. A Hermitian ZZ coupling is symmetric, so we use
  $(A_{ij} + A_{ji})/2$ and lose direction.
- Coherent dynamics is reversible, so a cascade can partly un-spread. We report peaks and time
  series, not a settled equilibrium.
- $\\Gamma$ flips agents even with no shock, so contagion is always reported against a no-shock
  baseline.
- No job has run on real IBM hardware yet. Hardware points are a noisy simulation using a fake
  backend, and they are labelled that way.

### References

Items marked ⚠️ are preprints, 2026 items, or details not yet checked against the source.

"""


def build():
    cells = [
        md(INTRO),
        md("## Setup"),
        code(SETUP),
        md("""
<a id="p1"></a>
## Part 1: The engine

`compile_ising` turns a network into a `SparsePauliOp`, using integer qubit indices so qubit
order can't be mistaken. `evolve` builds a Trotter circuit with `PauliEvolutionGate`, then
breaks it into real gates. That last step matters: since Qiskit 2.2, simulating an un-broken
evolution gate silently computes the exact answer, which would make any Trotter test meaningless.
"""),
        *embed(ENGINE),
        code(ENGINE_DEMO),
        md("""
<a id="p2"></a>
## Part 2: The spec language

An economy is a YAML file, and every number in it carries its source as a comment. A plugin
reads the spec and returns `(n, edges, h, gamma)`, so the three economies share one engine.

| Scenario | Qubit | $J$ (ZZ) | $h$ (Z) | $\\Gamma$ (X) |
|---|---|---|---|---|
| Contagion | Bank | Symmetrised Elliott–Golub–Jackson dependency | Basel III capital buffer, shock, bailout | Liquidity uncertainty |
| Inflation | Firm | Strategic complementarity in pricing | Credibility, money growth, VAT | Uncertainty about rivals |
| Compliance | Taxpayer | Social influence (Zaklan model) | Tax morale, audit × penalty, tax rate | Ambivalence |

The validator collects **every** problem and reports them together, before any simulation runs.
"""),
        *embed(SPECS + PLUGINS + QECON),
        code(VALIDATOR_DEMO),
        md("""
<a id="p3"></a>
## Part 3: Three economies

**Contagion.** Core-B fails. The gap between the lines is contagion: $\\Gamma$ moves agents even
with no shock, so the no-shock run is the fair comparison. The light-cone sorts banks by network
distance from Core-B. A bailout adds a solvency field to Core-A, and its row goes pale.
"""),
        code(SCENARIOS),
        md("**Inflation.** Expectations stay anchored at target, then de-anchor as money growth rises."),
        code(FIRMS),
        md("**Compliance.** Three evaders pull their neighbours along. More audits raise the floor."),
        code(TAXPAYERS),
        md("**Checking the headline claims.** This cell stops the notebook if a number at the top of this page is wrong."),
        code(CLAIMS),
        md("""
<a id="p4"></a>
## Part 4: Validation

How do we know the circuit computes what we say it computes? We built the same physics a second
way and measured the gap. `validation/reference.py` builds $H$ from the raw parameters using only
NumPy, because the engine's own `exact_state` shares its matrix with the circuit and would hide a
sign or qubit-order bug.

The test system is a 3×4 grid with a different $J$, $h$ and $\\Gamma$ on every site, because
uniform values hide qubit-order bugs and 1D chains are classically solvable.
"""),
        *embed(VALIDATION),
        code(VALIDATION_INTRO),
        md("""
**Trotter convergence and the $\\Gamma = 0$ test.** Error falls at the rate theory predicts. With
the transverse field off, every term commutes and nothing moves, which is why $\\Gamma$ is the
engine of the model. The result is zero to machine precision, not literally zero.
"""),
        code(figure("fig1_trotter")),
        md("""
**The memory wall.** This is the reason to use a quantum computer for this model. Exact memory
doubles with every agent, while gate counts from real compiled circuits grow with the number of
edges. It covers exact state vectors only.
"""),
        code(figure("fig2_memory_wall")),
        md("""
**Observable error.** First and second order overlap exactly on Z-basis numbers: they differ only
by diagonal phases, which can't change Z-basis probabilities from a basis-state start. So our specs
and hardware runs use first order, at half the two-qubit gates. $\\langle X \\rangle$ is not a
Z-basis number, and it shows the two really are different circuits.
"""),
        code(figure("fig5_observable_error")),
        md("""
**Against the classical model.** Glauber Monte Carlo uses the same $J$, $h$ and graph. It has a
heat bath, so it forgets its start and settles at a temperature-set equilibrium. The coherent
model conserves energy. These are different models, not faster and slower versions of one model.
"""),
        code(figure("fig4_glauber")),
        md("""
**Entanglement.** From a definite starting bit-string, entropy stays at zero with $\\Gamma = 0$
and grows with $\\Gamma$ on. This is a correlation measure of the model, not a claim about real people.
"""),
        code(figure("fig3_entropy")),
        md("""
<a id="p5"></a>
## Part 5: Hardware readiness

The same spec compiles to a real device through the Runtime Estimator with error mitigation. The
8-bank preset is the right size: at most 115 two-qubit gates after transpiling for a Heron device.

**No job has run on real hardware yet.** The table is a noisy simulation with `FakeBoston`, which
uses a real device's noise model. It separates hardware noise (device vs ideal, same circuit) from
Trotter error (ideal vs exact).
"""),
        *embed(HARDWARE),
        code(HARDWARE_DEMO),
        md(f"""
<a id="p6"></a>
## Part 6: The frontend

The live app lets you move policy levers and watch the economy respond. It has three scenarios,
a headline rewritten from the numbers on every run, counterfactuals, light-cones and a spec editor
that shows validator errors. It runs from `demo/streamlit_app.py`.
{f"**Try it:** [{APP_URL}]({APP_URL})" if APP_URL else ""}

The app calls `demo.server.api_run`, the same function as the local web demo in the repo, so both
share one tested path. The cell below uses that function and that chart. Press Play to watch a
bailed-out economy over time (needs an internet connection to load Plotly).
"""),
        *embed(FRONTEND),
        code(FRONTEND_DEMO),
        hidden(code("from base64 import b64decode\n\ndisplay(Image(data=b64decode(\""
                    + base64.b64encode((ROOT / "figures/streamlit_demo.jpg").read_bytes()).decode()
                    + "\"), width=900))"), "screenshot"),
        md("""
<a id="p7"></a>
## Part 7: The full test suite

The project's own tests run here against the code embedded above. Two groups run only from the
repo, because they need files that aren't embedded: the web-server tests and the headless tests of
the Streamlit app.
"""),
        *embed(TESTS),
        code(TESTS_RUN),
        md(LIMITS + citations()),
    ]
    notebook = new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    })
    nbformat.write(notebook, OUT)
    return notebook


def run(notebook):
    from nbclient import NotebookClient
    NotebookClient(notebook, timeout=900, kernel_name="python3",
                   resources={"metadata": {"path": str(ROOT)}}).execute()
    for cell in notebook.cells:
        if "source" in cell.metadata.get("tags", []):
            cell.outputs = []      # "Writing qecon_src/..." on 40 cells is just noise
        for output in cell.get("outputs", []):
            if output.output_type == "stream":     # keep local paths out of the submission
                output.text = output.text.replace(str(ROOT) + os.sep, "").replace(str(ROOT), ".")
    nbformat.write(notebook, OUT)


if __name__ == "__main__":
    built = build()
    print(f"{len(built.cells)} cells, {len(EMBEDDED)} embedded files")
    if "--no-run" not in sys.argv:
        run(built)
        print("ran clean:", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")
