/* QEcon demo front end: levers -> /api/run -> hand-drawn SVG views on one shared clock. */
"use strict";

const $ = (s) => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const COL = { blue: "#2a78d6", orange: "#eb6834", aqua: "#1baf7a", yellow: "#eda100",
  ink: "#121212", ink2: "#52514e", muted: "#898781", rule: "#e3dfd5", surface: "#fcfcfb" };
const RAMP = ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];

/* ---------------------------------------------------------------- helpers */
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function html(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const RAMP_RGB = RAMP.map(hex);
function rampColor(p) {
  p = Math.max(0, Math.min(1, p)) * (RAMP.length - 1);
  const i = Math.min(RAMP.length - 2, Math.floor(p)), f = p - i;
  const a = RAMP_RGB[i], b = RAMP_RGB[i + 1];
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(",")})`;
}
const inkOn = (p) => (p > 0.5 ? "#ffffff" : COL.ink);
const pct = (x, d = 0) => `${(x * 100).toFixed(d)}%`;
const pts = (x) => `${x >= 0 ? "+" : "−"}${Math.abs(Math.round(x * 100))}`;
const max = (a) => Math.max(...a);
const min = (a) => Math.min(...a);
const argmax = (a) => a.indexOf(max(a));
const argmin = (a) => a.indexOf(min(a));
function yamlNum(v, decimals, isInt) {
  if (isInt) return String(Math.round(v));
  let s = String(+(+v).toFixed(decimals));
  if (!s.includes(".") && !s.includes("e")) s += ".0";
  return s;
}
function humanBytes(b) {
  const u = ["B", "KB", "MB", "GB", "TB", "PB"];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return `${b < 10 && i ? b.toFixed(1) : Math.round(b)} ${u[i]}`;
}
function list(names) {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/* ---------------------------------------------------------------- scenarios */
const SCEN = {
  banks: {
    tab: "Contagion",
    kicker: "Scenario · Interbank contagion",
    state1: "insolvent",
    baselineLabel: "no shock (background)",
    dek: "Eight banks tied together by cross-holdings, using the Elliott–Golub–Jackson model. Each bank is a qubit: |0⟩ solvent, |1⟩ insolvent. One bank's capital is wiped out, and losses travel along exposures. Γ, liquidity uncertainty, lets every bank's state rotate.",
    mapping: [["J · ZZ", "exposure between banks, from the symmetrised EGJ dependency matrix"],
              ["h · Z", "capital above the Basel III 7% minimum; −2 on the failed bank; + bailout"],
              ["Γ · X", "liquidity and rollover uncertainty"]],
    defaults(spec) {
      return { seed: spec.initial.ones[0], bail: [], bailSize: spec.fields.bailout.strength,
               kappa: spec.fields.kappa, gamma: spec.uncertainty.gamma };
    },
    groups(spec, L) {
      const labels = spec.agents.labels;
      return [
        { title: "Shock", items: [
          { type: "radio", key: "seed", label: "Bank that fails", options: labels,
            maps: (v) => `starts in |1⟩ · h = −${spec.fields.shock.strength} on ${labels[v]}` } ] },
        { title: "Policy", items: [
          { type: "multi", key: "bail", label: "Bail out", options: labels, disabled: [L.seed],
            maps: (v) => (v.length ? `h += ${L.bailSize.toFixed(2)} on ${v.map((i) => labels[i]).join(", ")}` : "no intervention") },
          { type: "range", key: "bailSize", label: "Bailout size", min: 0, max: 4, step: 0.25, dec: 2,
            fmt: (v) => v.toFixed(2), unit: "J", maps: () => "extra solvency field, in units of the strongest exposure" },
          { type: "range", key: "kappa", label: "Capital sensitivity κ", min: 0, max: 0.3, step: 0.01, dec: 2,
            fmt: (v) => v.toFixed(2), maps: (v) => `h = ${v.toFixed(2)} × (CET1 − 7%)` } ] },
      ];
    },
    overrides(L) {
      return [`initial.ones=[${L.seed}]`, `fields.shock.nodes=[${L.seed}]`,
        `fields.bailout.nodes=[${L.bail.filter((b) => b !== L.seed).join(",")}]`,
        `fields.bailout.strength=${yamlNum(L.bailSize, 2)}`, `fields.kappa=${yamlNum(L.kappa, 2)}`,
        `uncertainty.gamma=${yamlNum(L.gamma, 2)}`];
    },
  },
  firms: {
    tab: "Inflation",
    kicker: "Scenario · Inflation expectations",
    state1: "raising prices",
    baselineLabel: "money growth on target",
    dek: "Twelve firms on a 4 × 3 supply grid. A firm raises its price when its neighbours do (strategic complementarity, Cooper & John). Money growth above the 2% target tilts every firm toward raising; central-bank credibility anchors them.",
    mapping: [["J · ZZ", "strategic complementarity in price setting between supply-chain neighbours"],
              ["h · Z", "anchor × credibility − 0.1 × (money growth − 2%) − 0.05 × ΔVAT"],
              ["Γ · X", "uncertainty about rivals' pricing"]],
    defaults(spec) {
      return { money: spec.fields.money_growth, cred: spec.fields.credibility,
               vat: spec.fields.vat_change, gamma: spec.uncertainty.gamma };
    },
    groups() {
      return [
        { title: "Monetary policy", items: [
          { type: "range", key: "money", label: "Money-supply growth", min: 0, max: 25, step: 1, dec: 0,
            fmt: (v) => `${v.toFixed(0)}%`, maps: (v) => `h −= 0.1 × (${v.toFixed(0)} − 2% target)`, ticks: ["0%", "25%"] },
          { type: "range", key: "cred", label: "Central-bank credibility", min: 0, max: 1, step: 0.05, dec: 2,
            fmt: (v) => v.toFixed(2), maps: (v) => `h += 1.0 × ${v.toFixed(2)}` } ] },
        { title: "Fiscal policy", items: [
          { type: "range", key: "vat", label: "VAT change", min: -5, max: 10, step: 0.5, dec: 1,
            fmt: (v) => `${v > 0 ? "+" : ""}${v.toFixed(1)} pp`, maps: (v) => `h −= 0.05 × ${v.toFixed(1)}` } ] },
      ];
    },
    overrides(L) {
      return [`fields.money_growth=${yamlNum(L.money, 0)}`, `fields.credibility=${yamlNum(L.cred, 2)}`,
        `fields.vat_change=${yamlNum(L.vat, 1)}`, `uncertainty.gamma=${yamlNum(L.gamma, 2)}`];
    },
  },
  taxpayers: {
    tab: "Compliance",
    kicker: "Scenario · Tax compliance",
    state1: "evading",
    baselineLabel: "no evader cluster",
    dek: "Twelve taxpayers on a lattice, three of them evading at the start: the Zaklan Ising model, made coherent. Audits and penalties add a compliance field; a tax rate above 30% pushes the other way; neighbours imitate each other.",
    mapping: [["J · ZZ", "social influence and conditional cooperation between neighbours"],
              ["h · Z", "tax morale + audit probability × penalty − 0.05 × (tax rate − 30%)"],
              ["Γ · X", "ambivalence"]],
    defaults(spec) {
      return { audit: spec.fields.audit_prob, penalty: spec.fields.penalty,
               rate: spec.fields.tax_rate, gamma: spec.uncertainty.gamma };
    },
    groups() {
      return [
        { title: "Enforcement", items: [
          { type: "range", key: "audit", label: "Audit probability", min: 0, max: 0.3, step: 0.01, dec: 2,
            fmt: (v) => pct(v), maps: (v) => `h += ${v.toFixed(2)} × penalty` },
          { type: "range", key: "penalty", label: "Penalty", min: 0, max: 20, step: 1, dec: 0, int: true,
            fmt: (v) => `${v.toFixed(0)} periods`, maps: () => "periods of forced honesty (Zaklan's k)" } ] },
        { title: "Tax", items: [
          { type: "range", key: "rate", label: "Tax rate", min: 10, max: 60, step: 1, dec: 0,
            fmt: (v) => `${v.toFixed(0)}%`, maps: (v) => `h −= 0.05 × (${v.toFixed(0)} − 30)` } ] },
      ];
    },
    overrides(L) {
      return [`fields.audit_prob=${yamlNum(L.audit, 2)}`, `fields.penalty=${yamlNum(L.penalty, 0, true)}`,
        `fields.tax_rate=${yamlNum(L.rate, 0)}`, `uncertainty.gamma=${yamlNum(L.gamma, 2)}`];
    },
  },
};
const GAMMA = { type: "range", key: "gamma", label: "Γ  transverse field", min: 0, max: 1.5, step: 0.05, dec: 2,
  fmt: (v) => v.toFixed(2), ticks: ["0 · classical", "1.5"],
  maps: (v) => (v === 0 ? "every term commutes: nothing can move" : "the only non-commuting term: lets decisions rotate") };

/* ---------------------------------------------------------------- state */
const S = { presets: null, scen: "banks", L: null, resp: null, t: 0, req: 0, timer: null, playing: null };

/* ---------------------------------------------------------------- levers */
function renderLevers() {
  const spec = S.presets[S.scen].spec;
  const sc = SCEN[S.scen];
  const rail = $("#levers");
  rail.innerHTML = "";
  const groups = [...sc.groups(spec, S.L), { title: "Uncertainty", note: "the quantum term", quantum: true, items: [GAMMA] }];
  for (const g of groups) {
    const box = html("section", `group${g.quantum ? " quantum" : ""}`);
    const t = html("h3", "group-title", g.title);
    if (g.note) { const em = html("em", null, g.note); t.appendChild(em); }
    box.appendChild(t);
    for (const it of g.items) box.appendChild(renderLever(it));
    rail.appendChild(box);
  }
  const foot = html("div", "rail-foot");
  const reset = html("button", "ghost", "Reset levers");
  reset.onclick = () => { S.L = sc.defaults(spec); renderLevers(); run(); };
  const specBtn = html("button", "ghost", "View spec");
  specBtn.onclick = openSheet;
  foot.append(reset, specBtn);
  rail.appendChild(foot);
}

function renderLever(it) {
  const wrap = html("div", "lever");
  const top = html("div", "lever-top");
  const label = html("span", "lever-label", it.label);
  top.appendChild(label);
  const maps = html("div", "lever-maps");
  if (it.type === "range") {
    const val = html("span", "lever-value");
    top.appendChild(val);
    const input = document.createElement("input");
    Object.assign(input, { type: "range", min: it.min, max: it.max, step: it.step, value: S.L[it.key] });
    input.setAttribute("aria-label", it.label);
    const sync = () => {
      const v = +input.value;
      val.textContent = it.fmt(v);
      maps.textContent = it.maps(v);
      input.style.setProperty("--pct", `${((v - it.min) / (it.max - it.min)) * 100}%`);
    };
    input.addEventListener("input", () => { S.L[it.key] = +input.value; sync(); schedule(); });
    sync();
    wrap.append(top, input);
    if (it.ticks) {
      const tk = html("div", "ticks");
      it.ticks.forEach((t) => tk.appendChild(html("span", null, t)));
      wrap.appendChild(tk);
    }
  } else {
    const chips = html("div", "chips");
    it.options.forEach((name, i) => {
      const b = html("button", `chip${it.type === "radio" ? " seed" : ""}`, name);
      const on = it.type === "radio" ? S.L[it.key] === i : S.L[it.key].includes(i);
      b.setAttribute("aria-pressed", on);
      if ((it.disabled || []).includes(i)) b.disabled = true;
      b.onclick = () => {
        if (it.type === "radio") {
          S.L[it.key] = i;
          S.L.bail = S.L.bail.filter((x) => x !== i);
        } else {
          const s = new Set(S.L[it.key]);
          s.has(i) ? s.delete(i) : s.add(i);
          S.L[it.key] = [...s].sort((a, b) => a - b);
        }
        renderLevers();
        run();
      };
      chips.appendChild(b);
    });
    maps.textContent = it.maps(S.L[it.key]);
    wrap.append(top, chips);
  }
  wrap.appendChild(maps);
  return wrap;
}

/* ---------------------------------------------------------------- running */
function schedule() {
  clearTimeout(S.timer);
  S.timer = setTimeout(run, 140);
}

async function run() {
  const id = ++S.req;
  const sc = SCEN[S.scen];
  const snap = JSON.parse(JSON.stringify(S.L));
  $("#stage").classList.add("loading");
  progress(true);
  $("#engine").className = "engine busy";
  try {
    const res = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: S.scen, overrides: sc.overrides(S.L), exact: true }) });
    const data = await res.json();
    if (id !== S.req) return;
    if (!res.ok) throw new Error(data.error || res.statusText);
    const first = !S.resp || S.resp.result.preset !== S.scen;
    S.resp = data;
    S.RL = snap;          // the levers this response was computed with
    const y = data.result.series[data.result.headline];
    const keepT = !first && S.playing === null;
    if (!keepT || S.t >= y.length) S.t = S.scen === "taxpayers" ? argmin(y) : argmax(y);
    render();
    const s = data.result.summary;
    $("#engine").className = "engine";
    $("#engine").textContent = `statevector · ${s.n} qubits · ${data.result.runtime_s.toFixed(2)} s`;
  } catch (err) {
    if (id !== S.req) return;
    $("#engine").className = "engine err";
    $("#engine").textContent = `error: ${err.message}`;
  } finally {
    if (id === S.req) { $("#stage").classList.remove("loading"); progress(false); }
  }
}

function progress(on) {
  const p = $("#progress");
  if (on) { p.className = "progress"; void p.offsetWidth; p.className = "progress on"; }
  else { p.className = "progress done"; }
}

/* ---------------------------------------------------------------- derived numbers */
function derived() {
  const { result: r, counterfactual: cf } = S.resp;
  const key = r.headline;
  const y = r.series[key];
  const base = r.baseline.series[key];
  const times = r.times;
  const low = S.scen === "taxpayers";
  const iPeak = low ? argmin(y) : argmax(y);
  const peak = y[iPeak];
  const basePeak = low ? min(base) : max(base);
  const excess = y.map((v, i) => v - base[i]);
  const cfy = cf ? cf.series[key] : null;
  const cfPeak = cfy ? (low ? min(cfy) : max(cfy)) : null;
  return { r, cf, key, y, base, times, iPeak, peak, basePeak, excess, cfy, cfPeak, low };
}

/* ---------------------------------------------------------------- render: words */
function renderLede(D) {
  const sc = SCEN[S.scen];
  const spec = S.presets[S.scen].spec;
  $("#kicker").textContent = sc.kicker;
  $("#dek").textContent = sc.dek;
  const N = (x) => `<span class="fig-num">${x}</span>`;
  const g0 = S.RL.gamma === 0;
  let h = "";
  if (S.scen === "banks") {
    const labels = spec.agents.labels;
    const seed = labels[S.RL.seed];
    const bail = S.RL.bail.filter((b) => b !== S.RL.seed).map((i) => labels[i]);
    const ratio = D.peak / Math.max(D.basePeak, 1e-9);
    if (g0) h = `With Γ = 0 every term commutes: <span class="hl">${seed}</span> stays failed and no other bank moves.`;
    else if (bail.length && D.cf) h = `Bailing out <span class="hl">${list(bail)}</span> holds peak insolvency to ${N(pct(D.peak))}, down from ${pct(D.cfPeak)} when ${seed} fails unchecked.`;
    else h = `When <span class="hl">${seed}</span> fails, up to ${N(pct(D.peak))} of the banking system is insolvent${ratio > 1.25 ? `, ${ratio.toFixed(1)}× the background rate.` : `, barely above background noise.`}`;
  } else if (S.scen === "firms") {
    const gap = D.peak - D.basePeak;
    if (g0) h = `With Γ = 0 nothing moves: firms hold their prices whatever the central bank does.`;
    else if (gap > 0.15) h = `At ${S.RL.money.toFixed(0)}% money growth, expectations de-anchor: up to ${N(pct(D.peak))} of firms raise prices.`;
    else if (gap > 0.04) h = `At ${S.RL.money.toFixed(0)}% money growth, up to ${N(pct(D.peak))} of firms raise prices, ${Math.round(gap * 100)} points above an economy on target.`;
    else h = `At ${S.RL.money.toFixed(0)}% money growth, expectations stay anchored: at most ${N(pct(D.peak))} of firms raise prices.`;
  } else {
    const start = D.y[0];
    if (g0) h = `With Γ = 0 nothing moves: the three evaders stay evaders and everyone else stays honest.`;
    else h = `With a ${pct(S.RL.audit)} audit rate, compliance bottoms out at ${N(pct(D.peak))}${D.peak < start - 0.03 ? ", as the evader cluster pulls its neighbours along." : ", and the evader cluster stays contained."}`;
  }
  $("#headline").innerHTML = h;
}

function stat(label, value, note, cls = "") {
  const d = html("div", "stat");
  d.appendChild(html("div", "stat-label", label));
  const v = html("div", `stat-value ${cls}`);
  v.innerHTML = value;
  d.appendChild(v);
  d.appendChild(html("div", "stat-note", note));
  return d;
}

function renderStats(D) {
  const box = $("#stats");
  box.innerHTML = "";
  const spec = S.presets[S.scen].spec;
  const tPk = D.times[D.iPeak].toFixed(2);
  const big = (x) => `${Math.round(x * 100)}<small>%</small>`;
  const delta = (x, goodWhenNegative = true) => {
    const good = goodWhenNegative ? x < 0 : x > 0;
    return [`${pts(x)}<small> pts</small>`, Math.abs(x) < 0.005 ? "" : good ? "delta-good" : "delta-bad"];
  };
  if (S.scen === "banks") {
    box.appendChild(stat("Peak share insolvent", big(D.peak), `at t = ${tPk}`));
    const ex = max(D.excess);
    box.appendChild(stat("Contagion", ...delta(ex, true).slice(0, 1), "peak excess over the no-shock background", ex > 0.005 ? "delta-bad" : ""));
    const P = D.r.per_agent.p_one, B = D.r.baseline.per_agent.p_one;
    let best = -1, bestV = -1;
    for (let i = 0; i < D.r.graph.n; i++) {
      if (i === S.RL.seed) continue;
      const v = max(P.map((row, k) => row[i] - B[k][i]));
      if (v > bestV) { bestV = v; best = i; }
    }
    const lab = spec.agents.labels[best];
    box.appendChild(stat("Most exposed", `<span style="font-size:26px">${lab}</span>`,
      `peak P(insolvent) ${pct(max(P.map((row) => row[best])))} vs ${pct(max(B.map((row) => row[best])))} background`));
    if (D.cf) {
      const [v, c] = delta(D.peak - D.cfPeak, true);
      box.appendChild(stat("Bailout effect", v, "on peak insolvency, vs the same shock unchecked", c));
    } else {
      box.appendChild(stat("Bailout effect", `<span style="color:var(--muted)">—</span>`, "choose a bank to bail out"));
    }
  } else if (S.scen === "firms") {
    box.appendChild(stat("Peak share raising prices", big(D.peak), `at t = ${tPk}`));
    const [v, c] = delta(D.peak - D.basePeak, true);
    box.appendChild(stat("Above an on-target economy", v, "peak, vs money growth at 2%", c));
    const half = D.y.findIndex((x) => x >= D.peak / 2);
    box.appendChild(stat("Time to half the peak", `${D.times[Math.max(0, half)].toFixed(2)}<small> /J</small>`, "how fast the shock propagates"));
    const sync = D.r.series.synchronization;
    box.appendChild(stat("Neighbour agreement", sync[D.iPeak].toFixed(2), "⟨ZᵢZⱼ⟩ over supply links at the peak"));
  } else {
    box.appendChild(stat("Lowest compliance", big(D.peak), `at t = ${tPk}`));
    const [v, c] = delta(D.peak - D.basePeak, false);
    box.appendChild(stat("Cost of the evader cluster", v, "vs the same lattice with no evaders", c));
    box.appendChild(stat("Compliance at the end", big(D.y[D.y.length - 1]), `t = ${D.times[D.times.length - 1].toFixed(1)}`));
    const sync = D.r.series.synchronization;
    box.appendChild(stat("Neighbour agreement", sync[D.iPeak].toFixed(2), "⟨ZᵢZⱼ⟩ over lattice links"));
  }
}

/* ---------------------------------------------------------------- render: time chart */
const CH = {};
function renderChart(D) {
  const host = $("#chart");
  host.innerHTML = "";
  const W = Math.max(320, host.clientWidth), H = 330;
  const m = { l: 44, r: 150, t: 12, b: 30 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const T = D.times;
  const x = (t) => m.l + (t / T[T.length - 1]) * iw;
  const y = (v) => m.t + (1 - v) * ih;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Headline over time" }, host);

  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    el("line", { x1: m.l, x2: m.l + iw, y1: y(v), y2: y(v), class: v === 0 ? "baseline-rule" : "gridline" }, svg);
    el("text", { x: m.l - 10, y: y(v) + 4, "text-anchor": "end", class: "tick-label" }, svg).textContent = `${v * 100}%`;
  }
  const tMax = T[T.length - 1];
  for (let t = 0; t <= tMax + 1e-9; t += tMax > 4 ? 1 : 0.5) {
    el("text", { x: x(t), y: H - 8, "text-anchor": "middle", class: "tick-label" }, svg).textContent = t.toFixed(0);
  }
  el("text", { x: m.l + iw, y: H - 8, "text-anchor": "end", class: "tick-label" }, svg).textContent = "";

  const sc = SCEN[S.scen];
  const series = [];
  series.push({ name: sc.baselineLabel, short: sc.baselineLabel, data: D.base, color: COL.aqua, w: 2 });
  if (D.cf) series.push({ name: S.resp.counterfactual_label, short: "no bailout", data: D.cfy, color: COL.orange, w: 2 });
  series.push({ name: "current policy", short: "current policy", data: D.y, color: COL.blue, w: 2.75 });
  const path = (d) => d.map((v, i) => `${i ? "L" : "M"}${x(T[i]).toFixed(1)},${y(v).toFixed(1)}`).join("");
  if (D.r.exact) {
    el("path", { d: path(D.r.exact.series[D.key]), class: "series", stroke: COL.ink, "stroke-width": 1.25,
      "stroke-dasharray": "1.5 3.5", opacity: 0.7 }, svg);
  }
  for (const s of series) el("path", { d: path(s.data), class: "series", stroke: s.color, "stroke-width": s.w }, svg);

  // hardware / noisy-simulator points
  const hw = S.resp.hardware || [];
  for (const d of hw) {
    const ys = d.series[D.key], es = (d.stds || {})[D.key] || [];
    d.times.forEach((t, i) => {
      if (es[i]) el("line", { x1: x(t), x2: x(t), y1: y(ys[i] - es[i]), y2: y(ys[i] + es[i]), stroke: COL.yellow, "stroke-width": 1.5 }, svg);
      el("rect", { x: x(t) - 5, y: y(ys[i]) - 5, width: 10, height: 10, fill: COL.yellow, stroke: COL.surface,
        "stroke-width": 2, transform: `rotate(45 ${x(t)} ${y(ys[i])})` }, svg);
    });
  }

  // direct end labels, nudged apart
  const ends = series.map((s) => ({ s, yy: y(s.data[s.data.length - 1]) })).sort((a, b) => a.yy - b.yy);
  for (let i = 1; i < ends.length; i++) ends[i].yy = Math.max(ends[i].yy, ends[i - 1].yy + 15);
  for (const e of ends) {
    const t = el("text", { x: m.l + iw + 10, y: e.yy + 4, class: "end-label" }, svg);
    t.textContent = e.s.short;
    t.style.fill = e.s.color === COL.blue ? COL.ink : COL.ink2;
    if (e.s.color === COL.blue) t.style.fontWeight = 600;
  }

  // legend
  const lg = $("#chart-legend");
  lg.innerHTML = "";
  const item = (color, label, cls = "") => {
    const sp = html("span");
    const i = html("i", cls);
    i.style.borderColor = color;
    sp.append(i, document.createTextNode(label));
    lg.appendChild(sp);
  };
  [...series].reverse().forEach((s) => item(s.color, s.name));
  if (D.r.exact) item(COL.ink, "exact (matrix exponential)", "dot");
  for (const d of hw) item(COL.yellow, `${d.backend}: ${d.kind}`, "dia");
  $("#chart-title").textContent = D.r.headline_label;

  // cursor + hover
  const cursor = el("g", {}, svg);
  const line = el("line", { y1: m.t, y2: m.t + ih, class: "cursor-line" }, cursor);
  const dots = series.map((s) => el("circle", { r: 4.5, fill: s.color, class: "cursor-dot" }, cursor));
  const hit = el("rect", { x: m.l, y: m.t, width: iw, height: ih, class: "hit" }, svg);
  const idxAt = (ev) => {
    const r = svg.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * W;
    const t = ((px - m.l) / iw) * tMax;
    let best = 0;
    T.forEach((tt, i) => { if (Math.abs(tt - t) < Math.abs(T[best] - t)) best = i; });
    return best;
  };
  hit.addEventListener("mousemove", (ev) => {
    const i = idxAt(ev);
    setT(i);
    const rows = [...series].reverse().map((s) => [s.color, s.name, pct(s.data[i], 1)]);
    if (D.r.exact) rows.push([COL.ink, "exact", pct(D.r.exact.series[D.key][i], 1)]);
    tooltip(ev, `t = ${T[i].toFixed(2)}`, rows);
  });
  hit.addEventListener("mouseleave", hideTooltip);
  hit.addEventListener("click", (ev) => setT(idxAt(ev)));
  Object.assign(CH, { x, y, T, line, dots, series });
}

/* ---------------------------------------------------------------- render: network */
const NET = {};
function renderNetwork(D) {
  const host = $("#network");
  host.innerHTML = "";
  const g = D.r.graph, n = g.n;
  const W = Math.max(300, host.clientWidth), H = 360, pad = 46, R = n > 10 ? 19 : 22;
  const P = Object.keys(g.positions).map((k) => g.positions[k]);
  const xs = P.map((p) => p[0]), ys = P.map((p) => p[1]);
  const [x0, x1, y0, y1] = [min(xs), max(xs), min(ys), max(ys)];
  const sc = Math.min((W - 2 * pad) / Math.max(x1 - x0, 1e-9), (H - 2 * pad - 14) / Math.max(y1 - y0, 1e-9));
  const ox = (W - (x1 - x0) * sc) / 2, oy = (H - 14 - (y1 - y0) * sc) / 2;
  const px = (i) => ox + (g.positions[i][0] - x0) * sc;
  const py = (i) => oy + (y1 - g.positions[i][1]) * sc;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Agent network" }, host);
  const jmax = max(g.edges.map((e) => e[2])) || 1;
  for (const [i, j, J] of g.edges) {
    el("line", { x1: px(i), y1: py(i), x2: px(j), y2: py(j), class: "edge", "stroke-width": (0.8 + 4.2 * J / jmax).toFixed(2),
      opacity: (0.45 + 0.55 * J / jmax).toFixed(2) }, svg);
  }
  const spec = S.presets[S.scen].spec;
  const bailed = S.scen === "banks" ? S.RL.bail.filter((b) => b !== S.RL.seed) : [];
  const nodes = [], labels = [];
  for (let i = 0; i < n; i++) {
    const gx = px(i), gy = py(i);
    if (g.init_ones.includes(i)) el("circle", { cx: gx, cy: gy, r: R + 5, class: "ring-seed" }, svg);
    if (bailed.includes(i)) el("circle", { cx: gx, cy: gy, r: R + 5, class: "ring-bail" }, svg);
    const c = el("circle", { cx: gx, cy: gy, r: R, class: "node", fill: rampColor(D.r.per_agent.p_one[Math.min(S.t, D.times.length - 1)][i]), stroke: "#ffffff", "stroke-width": 1.5 }, svg);
    const tx = el("text", { x: gx, y: gy + 0.5, class: "node-pct" }, svg);
    const lb = el("text", { x: gx, y: gy + R + 17, class: "node-label" }, svg);
    lb.textContent = D.r.labels[i].replace("Firm ", "").replace("Taxpayer ", "");
    c.addEventListener("mousemove", (ev) => {
      const p = D.r.per_agent.p_one[S.t][i];
      const rows = [[null, `P(${SCEN[S.scen].state1})`, pct(p, 1)], [null, "field h", g.h[i].toFixed(2)],
        [null, "Γ", g.gamma[i].toFixed(2)], [null, "links from shock", g.distance_from_seed[i]]];
      tooltip(ev, D.r.labels[i], rows);
    });
    c.addEventListener("mouseleave", hideTooltip);
    nodes.push(c); labels.push(tx);
  }
  const lg = $("#net-legend");
  lg.innerHTML = `<span>0%</span><span class="bar"></span><span>100% ${SCEN[S.scen].state1}</span>`;
  $("#net-title").textContent = S.scen === "banks" ? "The network · ring = failed bank, dashed = bailed out"
    : S.scen === "firms" ? "The supply grid" : "The lattice · ring = initial evaders";
  Object.assign(NET, { nodes, labels, D });
}

/* ---------------------------------------------------------------- render: light-cone */
const CONE = [];
function renderCone(D) {
  const host = $("#cone");
  host.innerHTML = "";
  CONE.length = 0;
  const sc = SCEN[S.scen];
  const panels = [{ r: D.r, title: "Current policy", color: COL.blue, P: D.r.per_agent.p_one }];
  if (D.cf) panels.push({ r: D.cf, title: "Same shock, no bailout", color: COL.orange, P: D.cf.per_agent.p_one });
  else panels.push({ r: D.r, title: `Comparison: ${sc.baselineLabel}`, color: COL.aqua, P: D.r.baseline.per_agent.p_one });
  host.className = "cone-grid";
  const g = D.r.graph;
  const dist = g.distance_from_seed.map((d) => (d < 0 ? 99 : d));
  const order = [...Array(g.n).keys()].sort((a, b) => dist[a] - dist[b] || a - b);
  for (const pnl of panels) {
    const box = html("div");
    const t = html("p", "cone-title");
    const sw = html("i"); sw.style.borderColor = pnl.color;
    t.append(sw, document.createTextNode(pnl.title));
    box.appendChild(t);
    host.appendChild(box);
    const W = Math.max(300, box.clientWidth), rowH = g.n > 10 ? 22 : 26, lw = 112;
    const H = rowH * g.n + 30;
    const T = D.times, cw = (W - lw - 4) / T.length;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": pnl.title }, box);
    order.forEach((ag, row) => {
      const yy = row * rowH;
      el("text", { x: 0, y: yy + rowH / 2 + 4, class: "row-label" }, svg).textContent =
        D.r.labels[ag].replace("Firm ", "").replace("Taxpayer ", "");
      el("text", { x: lw - 8, y: yy + rowH / 2 + 4, "text-anchor": "end", class: "row-dist" }, svg).textContent =
        dist[ag] === 99 ? "" : `d${dist[ag]}`;
      T.forEach((tt, k) => {
        const p = pnl.P[k][ag];
        const c = el("rect", { x: lw + k * cw, y: yy + 1, width: Math.max(1, cw - 1.5), height: rowH - 2.5, rx: 1.5, fill: rampColor(p) }, svg);
        c.addEventListener("mousemove", (ev) => {
          setT(k);
          tooltip(ev, `${D.r.labels[ag]} · t = ${tt.toFixed(2)}`, [[null, `P(${sc.state1})`, pct(p, 1)]]);
        });
        c.addEventListener("mouseleave", hideTooltip);
      });
    });
    const tMax = T[T.length - 1];
    for (let tt = 0; tt <= tMax + 1e-9; tt += tMax > 4 ? 1 : 0.5) {
      el("text", { x: lw + (tt / tMax) * (T.length - 1) * cw + cw / 2, y: H - 8, "text-anchor": "middle", class: "tick-label" }, svg)
        .textContent = tt.toFixed(0);
    }
    const cur = el("rect", { y: -2, width: cw + 0.5, height: rowH * g.n + 3, fill: "none", stroke: COL.ink, "stroke-width": 1.25, rx: 2 }, svg);
    CONE.push({ cur, lw, cw });
  }
}

/* ---------------------------------------------------------------- render: under the hood */
function renderHood(D) {
  const sc = SCEN[S.scen];
  const map = $("#mapping");
  map.innerHTML = "";
  for (const [k, v] of sc.mapping) { map.appendChild(html("dt", null, k)); map.appendChild(html("dd", null, v)); }
  const s = D.r.summary;
  const facts = $("#facts");
  facts.innerHTML = "";
  const add = (k, v, note) => {
    facts.appendChild(html("dt", null, k));
    const dd = html("dd", null, v);
    if (note) dd.appendChild(html("small", null, note));
    facts.appendChild(dd);
  };
  add("qubits", `${s.n}`, "one per agent");
  add("couplings", `${s.edges}`, "ZZ terms");
  add("exact memory", humanBytes(s.statevector_bytes), "16 · 2ⁿ bytes, doubles per agent");
  add("2q gates / step", `~${s.cx_per_step}`, "CX, before routing; linear in couplings");
  add("Trotter steps", `${s.trotter_steps_at_t_max}`, `at t = ${D.times[D.times.length - 1]}, 2nd order`);
  if (D.r.trotter_max_error !== undefined) add("max |circuit − exact|", D.r.trotter_max_error.toExponential(1), "on the headline");
  add("runtime", `${D.r.runtime_s.toFixed(2)} s`, s.method === "incremental" ? "same circuits, block by block" : "");
  for (const d of S.resp.hardware || []) {
    const st = d.circuit_stats || [];
    add("device run", d.backend, `${d.kind}; ${st.map((x) => x.two_qubit_gates).join("/")} two-qubit gates`);
  }
  const src = $("#sources");
  src.innerHTML = "";
  for (const [k, v] of Object.entries(D.r.sources || {})) {
    const li = html("li");
    li.innerHTML = `<b>${k}</b> · `;
    li.appendChild(document.createTextNode(v));
    src.appendChild(li);
  }
}

/* ---------------------------------------------------------------- the clock */
function setT(i) {
  if (!S.resp) return;
  S.t = i;
  const D = NET.D;
  const r = D.r;
  if (CH.line) {
    const xx = CH.x(CH.T[i]);
    CH.line.setAttribute("x1", xx); CH.line.setAttribute("x2", xx);
    CH.series.forEach((s, k) => { CH.dots[k].setAttribute("cx", xx); CH.dots[k].setAttribute("cy", CH.y(s.data[i])); });
  }
  const P = r.per_agent.p_one[i];
  NET.nodes.forEach((c, k) => {
    c.setAttribute("fill", rampColor(P[k]));
    NET.labels[k].textContent = `${Math.round(P[k] * 100)}`;
    NET.labels[k].setAttribute("fill", inkOn(P[k]));
  });
  for (const c of CONE) c.cur.setAttribute("x", c.lw + i * c.cw - 0.25);
  const slider = $("#time");
  slider.value = i;
  slider.style.setProperty("--pct", `${(i / Math.max(1, r.times.length - 1)) * 100}%`);
  $("#time-readout").textContent = `t = ${r.times[i].toFixed(2)}`;
}

function render() {
  const D = derived();
  NET.D = D;
  renderLede(D);
  renderStats(D);
  renderChart(D);
  renderNetwork(D);
  renderCone(D);
  renderHood(D);
  const slider = $("#time");
  slider.max = D.times.length - 1;
  setT(Math.min(S.t, D.times.length - 1));
}

function togglePlay() {
  const icon = $("#play-icon");
  if (S.playing !== null) {
    clearInterval(S.playing); S.playing = null;
    icon.innerHTML = '<path d="M4 2.5v11l9-5.5z"/>';
    return;
  }
  const T = S.resp.result.times.length;
  if (S.t >= T - 1) setT(0);
  icon.innerHTML = '<path d="M4 3h3v10H4zM9 3h3v10H9z"/>';
  S.playing = setInterval(() => {
    if (S.t >= T - 1) { togglePlay(); return; }
    setT(S.t + 1);
  }, 110);
}

/* ---------------------------------------------------------------- tooltip */
function tooltip(ev, head, rows) {
  const tt = $("#tooltip");
  tt.innerHTML = "";
  tt.appendChild(html("div", "tt-head", head));
  for (const [color, k, v] of rows) {
    const row = html("div", "tt-row");
    const left = html("span");
    if (color) { const sw = html("i", "sw"); sw.style.background = color; left.appendChild(sw); }
    left.appendChild(document.createTextNode(k));
    const b = html("b", null, String(v));
    row.append(left, b);
    tt.appendChild(row);
  }
  tt.classList.add("on");
  const w = tt.offsetWidth, h = tt.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
  tt.style.left = `${x}px`; tt.style.top = `${y}px`;
}
function hideTooltip() { $("#tooltip").classList.remove("on"); }

/* ---------------------------------------------------------------- spec sheet */
function openSheet() {
  $("#yaml").value = S.presets[S.scen].yaml;
  $("#validator").innerHTML = "";
  $("#sheet").classList.add("open");
  $("#sheet").setAttribute("aria-hidden", "false");
}
function closeSheet() {
  $("#sheet").classList.remove("open");
  $("#sheet").setAttribute("aria-hidden", "true");
}
async function runYaml() {
  const out = $("#validator");
  out.innerHTML = '<span style="color:var(--muted)">validating…</span>';
  const res = await fetch("/api/run_yaml", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml: $("#yaml").value }) });
  const d = await res.json();
  out.innerHTML = "";
  if (d.ok) {
    out.appendChild(html("div", "ok", `✓ Valid. Compiled ${d.n} qubits and simulated: ${d.headline.replace(/_/g, " ")} reaches ${pct(d.peak)}.`));
  } else {
    out.appendChild(html("div", "bad-title", d.title || "Rejected"));
    const ul = html("ul");
    for (const e of d.errors) ul.appendChild(html("li", null, e));
    out.appendChild(ul);
  }
}

/* ---------------------------------------------------------------- boot */
function selectScenario(name) {
  S.scen = name;
  S.L = SCEN[name].defaults(S.presets[name].spec);
  document.querySelectorAll(".scenarios button").forEach((b) => b.setAttribute("aria-selected", b.dataset.s === name));
  if (S.playing !== null) togglePlay();
  renderLevers();
  run();
}

async function boot() {
  const res = await fetch("/api/presets");
  S.presets = await res.json();
  const nav = $("#scenarios");
  for (const [k, sc] of Object.entries(SCEN)) {
    const b = html("button", null, sc.tab);
    b.dataset.s = k;
    b.setAttribute("role", "tab");
    b.onclick = () => selectScenario(k);
    nav.appendChild(b);
  }
  $("#play").onclick = togglePlay;
  $("#time").addEventListener("input", (e) => setT(+e.target.value));
  $("#open-spec").onclick = openSheet;
  $("#close-spec").onclick = closeSheet;
  $("#sheet").addEventListener("click", (e) => { if (e.target.id === "sheet") closeSheet(); });
  $("#run-yaml").onclick = runYaml;
  $("#reset-yaml").onclick = () => { $("#yaml").value = S.presets[S.scen].yaml; $("#validator").innerHTML = ""; };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSheet();
    if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
    if (e.key === " ") { e.preventDefault(); togglePlay(); }
    if (e.key === "ArrowRight" && S.resp) setT(Math.min(S.t + 1, S.resp.result.times.length - 1));
    if (e.key === "ArrowLeft" && S.resp) setT(Math.max(S.t - 1, 0));
  });
  let rz;
  addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => S.resp && render(), 120); });
  selectScenario("banks");
}
boot();
