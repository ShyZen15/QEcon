"""Shared chart style and output helpers, so all five figures read as one set."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#8a8983"
GRID = "#e6e5e0"

# Fixed order, checked with the palette validator. Colour follows the entity.
BLUE = "#2a78d6"     # first order / coherent / Gamma > 0
ORANGE = "#eb6834"   # second order
AQUA = "#1baf7a"     # Gamma = 0 / classical reference

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.size": 13,
    "font.family": "sans-serif",
    "text.color": INK,
    "axes.labelcolor": INK_SECONDARY,
    "axes.titlecolor": INK,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.edgecolor": INK_MUTED,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "xtick.minor.visible": False,
    "ytick.minor.visible": False,
    "lines.linewidth": 2.0,
    "lines.markersize": 7,
    "legend.frameon": False,
    "legend.fontsize": 12,
})


def heading(fig, title, subtitle=None):
    """Claim-style title in the top-left, with an optional line of conditions under it."""
    fig.text(0.015, 0.975, title, fontsize=18, fontweight="bold", color=INK, va="top")
    if subtitle:
        fig.text(0.015, 0.905, subtitle, fontsize=12.5, color=INK_SECONDARY, va="top")


def save(fig, name, data):
    """Writes figures/<name>.png and figures/<name>.json. Slides quote the JSON."""
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT / name}.png")
