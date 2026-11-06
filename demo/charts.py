"""Plotly figures for the demo. Fixed categorical order (blue, orange, aqua, yellow),
one-hue blue ramp for P(state 1), recessive axes, text in ink colours."""
import numpy as np
import plotly.graph_objects as go

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
RAMP = [[0.0, "#f4f8fd"], [0.2, "#cde2fb"], [0.4, "#86b6ef"], [0.6, "#3987e5"],
        [0.8, "#1c5cab"], [1.0, "#0d366b"]]


def _layout(fig, title, height=420, **kw):
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=INK)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        margin=dict(l=10, r=10, t=50, b=10), font=dict(color=INK2, size=12),
        hoverlabel=dict(bgcolor="white", font_color=INK), **kw)
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont_color=MUTED)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont_color=MUTED)
    return fig


def headline_chart(r, rc=None, rc_label=None, hw=(), baseline_label="baseline"):
    key = r["headline"]
    t = r["times"]
    fig = go.Figure()
    if "baseline" in r:
        fig.add_trace(go.Scatter(x=t, y=r["baseline"]["series"][key], name=baseline_label,
                                 line=dict(color=AQUA, width=2)))
    if rc is not None:
        fig.add_trace(go.Scatter(x=t, y=rc["series"][key], name=rc_label,
                                 line=dict(color=ORANGE, width=2)))
    fig.add_trace(go.Scatter(x=t, y=r["series"][key], name="current policy (Trotter circuit)",
                             line=dict(color=BLUE, width=2.5)))
    if "exact" in r:
        fig.add_trace(go.Scatter(x=t, y=r["exact"]["series"][key], name="exact expm",
                                 line=dict(color=INK2, width=1.2, dash="dot")))
    for d in hw:
        err = d.get("stds", {}).get(key)
        fig.add_trace(go.Scatter(
            x=d["times"], y=d["series"][key], mode="markers",
            name=f"{d.get('backend', 'hardware')} ({d.get('kind', 'hardware')})",
            marker=dict(color=YELLOW, size=11, symbol="diamond",
                        line=dict(color=SURFACE, width=2)),
            error_y=dict(type="data", array=err, visible=err is not None, color=YELLOW)))
    fig.update_yaxes(range=[-0.02, 1.02], tickformat=".0%", title=r["headline_label"])
    fig.update_xaxes(title="time (units of 1/J)")
    fig.update_traces(hovertemplate="t = %{x:.2f}<br>%{y:.1%}")
    return _layout(fig, r["headline_label"], hovermode="x unified",
                   legend=dict(orientation="h", y=-0.22, x=0))


def _sorted(r):
    d = np.array(r["graph"]["distance_from_seed"])
    d = np.where(d < 0, d.max() + 1, d)
    return np.argsort(d, kind="stable"), d


def heatmap(r, title):
    order, d = _sorted(r)
    P = np.array(r["per_agent"]["p_one"])[:, order].T
    names = [f"{r['labels'][i]} (d={d[i]})" for i in order]
    fig = go.Figure(go.Heatmap(
        z=P, x=r["times"], y=names, zmin=0, zmax=1, colorscale=RAMP, xgap=1, ygap=2,
        colorbar=dict(title=f"P({r['states']['1']})", tickformat=".0%", outlinewidth=0),
        hovertemplate="%{y}<br>t = %{x:.2f}<br>P = %{z:.1%}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", gridcolor=SURFACE)
    fig.update_xaxes(title="time (units of 1/J)", gridcolor=SURFACE)
    return _layout(fig, title, height=max(320, 32 * len(order) + 120))


def network_chart(r):
    """Agents as nodes coloured by P(state 1), animated over time (play button + slider)."""
    g = r["graph"]
    pos = np.array([g["positions"][str(i)] for i in range(g["n"])])
    P = np.array(r["per_agent"]["p_one"])
    t = r["times"]
    jmax = max((e[2] for e in g["edges"]), default=1.0) or 1.0

    edge_traces = []
    for i, j, J in g["edges"]:
        edge_traces.append(go.Scatter(
            x=[pos[i, 0], pos[j, 0]], y=[pos[i, 1], pos[j, 1]], mode="lines",
            line=dict(color=AXIS, width=1 + 4 * J / jmax), hoverinfo="skip", showlegend=False))

    def nodes(k):
        return go.Scatter(
            x=pos[:, 0], y=pos[:, 1], mode="markers+text", text=r["labels"],
            textposition="top center", textfont=dict(size=11, color=INK2),
            customdata=np.stack([P[k], g["h"]], axis=1),
            hovertemplate="%{text}<br>P(" + r["states"]["1"] + ") = %{customdata[0]:.1%}"
                          "<br>h = %{customdata[1]:.2f}<extra></extra>",
            marker=dict(size=34, color=P[k], cmin=0, cmax=1, colorscale=RAMP,
                        line=dict(color=[INK if i in g["init_ones"] else SURFACE
                                         for i in range(g["n"])], width=2.5),
                        colorbar=dict(title=f"P({r['states']['1']})", tickformat=".0%",
                                      outlinewidth=0, len=0.8)),
            showlegend=False)

    # open on the moment the headline peaks, so a slider change is visible immediately
    y = np.array(r["series"][r["headline"]])
    start = int(np.argmin(y) if r.get("states", {}).get("0") == "comply" else np.argmax(y))
    fig = go.Figure(data=edge_traces + [nodes(start)])
    ne = len(edge_traces)
    fig.frames = [go.Frame(data=[nodes(k)], traces=[ne], name=f"{t[k]:.2f}")
                  for k in range(len(t))]
    fig.update_layout(
        updatemenus=[dict(type="buttons", x=0, y=-0.02, xanchor="left", yanchor="top",
                          direction="left", pad=dict(t=0, r=8),
                          buttons=[dict(label="▶ Play", method="animate",
                                        args=[None, dict(frame=dict(duration=180, redraw=True),
                                                         transition=dict(duration=0),
                                                         fromcurrent=True)]),
                                   dict(label="❚❚", method="animate",
                                        args=[[None], dict(mode="immediate",
                                                           frame=dict(duration=0))])])],
        sliders=[dict(active=start, x=0.17, len=0.83, y=-0.02, yanchor="top", pad=dict(t=0),
                      currentvalue=dict(prefix="t = ", font=dict(color=INK2)),
                      font=dict(color="rgba(0,0,0,0)"), ticklen=0, minorticklen=0,
                      tickcolor="rgba(0,0,0,0)",
                      steps=[dict(label=f.name, method="animate",
                                  args=[[f.name], dict(mode="immediate",
                                                       frame=dict(duration=0, redraw=True))])
                             for f in fig.frames])])
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x")
    return _layout(fig, f"Network at t = {t[start]:.2f} (peak): colour = P({r['states']['1']}), "
                        "outlined = seeded",
                   height=470)
