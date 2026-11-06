"""Static figures for the CLI and the deck (matplotlib, PNG).

Colors: categorical slots in fixed order (blue, orange, aqua, yellow), one-hue blue
ramp for magnitude (P(state 1)), recessive gray axes/grid, text in ink colors only.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE_RAMP = LinearSegmentedColormap.from_list(
    "blue_ramp", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "lines.linewidth": 2.0, "legend.frameon": False,
})


def _sorted_agents(result):
    d = np.array(result["graph"]["distance_from_seed"])
    d = np.where(d < 0, d.max() + 1, d)
    return np.argsort(d, kind="stable"), d


def _heatmap(ax, result, title):
    order, d = _sorted_agents(result)
    P = np.array(result["per_agent"]["p_one"])[:, order].T
    t = np.array(result["times"])
    im = ax.imshow(P, aspect="auto", origin="upper", cmap=BLUE_RAMP, vmin=0, vmax=1,
                   extent=[t[0], t[-1], len(order) - 0.5, -0.5], interpolation="nearest")
    labels = [f"{result['labels'][i]}  (d={d[i]})" for i in order]
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(labels, fontsize=8, color=INK2)
    ax.set_xlabel("time (units of 1/J)")
    ax.set_title(title, loc="left")
    ax.grid(False)
    return im


def plot_result(result, path):
    """Left: headline series vs time (exact overlay if present). Right: per-agent heatmap."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1, 1.15]})
    t = result["times"]
    key = result["headline"]
    a1.plot(t, result["series"][key], color=SERIES[0], label="Trotter circuit")
    a1.plot(t, result["series"][key], "o", color=SERIES[0], ms=4,
            markeredgecolor=SURFACE, markeredgewidth=1)
    if "exact" in result:
        a1.plot(t, result["exact"]["series"][key], "--", color=INK2, lw=1.2,
                label=f"exact expm (max err {result['trotter_max_error']:.1e})")
        a1.legend(loc="best", fontsize=8)
    a1.set_ylim(-0.02, 1.02)
    a1.set_xlabel("time (units of 1/J)")
    a1.set_ylabel(result["headline_label"])
    s = result["summary"]
    a1.set_title(f"{result['name']}  ·  {s['n']} agents, {s['edges']} edges", loc="left")
    im = _heatmap(a2, result, f"P({result['states']['1']}) per agent, sorted by distance from seed")
    cb = fig.colorbar(im, ax=a2, fraction=0.04, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=MUTED)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_compare(results, names, path, title, ylabel=None):
    """Headline series from several runs on one axis (<= 4 runs: direct-labeled + legend)."""
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ends = []
    for k, (r, nm) in enumerate(zip(results, names)):
        y = r["series"][r["headline"]]
        ax.plot(r["times"], y, color=SERIES[k], label=nm)
        ends.append([y[-1], nm, r["times"][-1]])
    if len(results) <= 4:
        # direct labels at line ends, nudged apart so they never overlap
        ends.sort(key=lambda e: e[0])
        gap = 0.05
        for a in range(1, len(ends)):
            ends[a][0] = max(ends[a][0], ends[a - 1][0] + gap)
        for ylab, nm, tend in ends:
            ax.annotate(nm, (tend, ylab), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=8, color=INK2, annotation_clip=False)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("time (units of 1/J)")
    ax.set_ylabel(ylabel or results[0]["headline_label"])
    ax.set_title(title, loc="left")
    ax.legend(loc="upper left", fontsize=8)
    ax.margins(x=0)
    fig.tight_layout()
    fig.subplots_adjust(right=0.74)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_lightcone_pair(r_left, r_right, path, left_title, right_title):
    """Two heatmaps on one color scale: e.g. no bailout vs bailout."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    im = _heatmap(axes[0], r_left, left_title)
    _heatmap(axes[1], r_right, right_title)
    axes[1].tick_params(labelleft=False)
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label(f"P({r_left['states']['1']})", color=INK2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=MUTED)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path
