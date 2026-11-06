/* QEcon demo front end: levers -> /api/run -> hand-drawn SVG views on one shared clock. */
"use strict";

const $ = (s) => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";

/* ---------------------------------------------------------------- theme */
// Sequential ramps for P(state 1): low = close to the card surface, high = strong.
// Dark mode is its own ramp (light = high), not an inversion of the light one.
const RAMPS = {
  light: ["#f2f6fc", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],
  dark: ["#1f2633", "#173a66", "#1c5cab", "#3987e5", "#86b6ef", "#d6e6fb"],
};
const COL = {};
let RAMP_RGB = [];
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
function readTheme() {
  const cs = getComputedStyle(document.documentElement);
  for (const k of ["blue", "orange", "aqua", "yellow", "ink", "ink-2", "muted", "surface", "rule", "bad", "good"]) {
    COL[k.replace("-", "")] = cs.getPropertyValue(`--${k}`).trim();
  }
  const theme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  RAMP_RGB = RAMPS[theme].map(hex);
  const grad = `linear-gradient(90deg, ${RAMPS[theme].join(", ")})`;
  document.querySelectorAll(".ramp-legend .bar").forEach((b) => (b.style.background = grad));
}
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem("qecon-theme", t);
  readTheme();
  if (S.resp) render();
}

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
function rampRGB(p) {
  p = Math.max(0, Math.min(1, p)) * (RAMP_RGB.length - 1);
  const i = Math.min(RAMP_RGB.length - 2, Math.floor(p)), f = p - i;
  const a = RAMP_RGB[i], b = RAMP_RGB[i + 1];
  return a.map((v, k) => Math.round(v + (b[k] - v) * f));
}
const rampColor = (p) => `rgb(${rampRGB(p).join(",")})`;
function inkOn(p) {
  const [r, g, b] = rampRGB(p).map((v) => v / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45 ? "#141414" : "#ffffff";
}
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
const list = (n) => (n.length <= 1 ? n.join("") : `${n.slice(0, -1).join(", ")} and ${n[n.length - 1]}`);
const short = (s) => s.replace("Firm ", "").replace("Taxpayer ", "");

/* ---------------------------------------------------------------- scenarios */
const SCEN = {
  banks: {
    tab: "Contagion",
    kicker: "Interbank contagion",
    state1: "insolvent",
    baselineLabel: "no shock",
    dek: "Eight banks linked by cross-holdings (Elliott–Golub–Jackson). Each bank is a qubit: |0⟩ solvent, |1⟩ insolvent. One bank's capital is wiped out; losses travel along exposures.",
    mapping: [["J · ZZ", "exposure between banks (symmetrised EGJ dependency matrix)"],
              ["h · Z", "capital above the Basel III 7% minimum; −2 on the failed bank; + bailout"],
              ["Γ · X", "liquidity and rollover uncertainty"]],
    defaults: (s) => ({ seed: s.initial.ones[0], bail: [], bailSize: s.fields.bailout.strength,
                        kappa: s.fields.kappa, gamma: s.uncertainty.gamma }),
    groups(spec, L) {
      const labels = spec.agents.labels;
      return [
        { title: "Shock", items: [
          { type: "radio", key: "seed", label: "Bank that fails", options: labels,
            maps: (v) => `starts in |1⟩, h = −${spec.fields.shock.strength} on ${labels[v]}` } ] },
        { title: "Policy", items: [
          { type: "multi", key: "bail", label: "Bail out", options: labels, disabled: [L.seed],
            maps: (v) => (v.length ? `h += ${L.bailSize.toFixed(2)} on ${v.map((i) => labels[i]).join(", ")}` : "no intervention") },
          { type: "range", key: "bailSize", label: "Bailout size", min: 0, max: 4, step: 0.25,
            fmt: (v) => v.toFixed(2), maps: () => "extra solvency field, in units of J" },
          { type: "range", key: "kappa", label: "Capital sensitivity κ", min: 0, max: 0.3, step: 0.01,
            fmt: (v) => v.toFixed(2), maps: (v) => `h = ${v.toFixed(2)} × (CET1 − 7%)` } ] },
      ];
    },
    overrides: (L) => [`initial.ones=[${L.seed}]`, `fields.shock.nodes=[${L.seed}]`,
      `fields.bailout.nodes=[${L.bail.filter((b) => b !== L.seed).join(",")}]`,
      `fields.bailout.strength=${yamlNum(L.bailSize, 2)}`, `fields.kappa=${yamlNum(L.kappa, 2)}`,
      `uncertainty.gamma=${yamlNum(L.gamma, 2)}`],
  },
  firms: {
    tab: "Inflation",
    kicker: "Inflation expectations",
    state1: "raising prices",
    baselineLabel: "money on target",
    dek: "Twelve firms on a 4 × 3 supply grid. A firm raises its price when its neighbours do. Money growth above the 2% target tilts every firm toward raising; credibility anchors them.",
    mapping: [["J · ZZ", "strategic complementarity in pricing between supply-chain neighbours"],
              ["h · Z", "anchor × credibility − 0.1 × (money growth − 2%) − 0.05 × ΔVAT"],
              ["Γ · X", "uncertainty about rivals' pricing"]],
    defaults: (s) => ({ money: s.fields.money_growth, cred: s.fields.credibility, vat: s.fields.vat_change, gamma: s.uncertainty.gamma }),
    groups: () => [
      { title: "Monetary policy", items: [
        { type: "range", key: "money", label: "Money-supply growth", min: 0, max: 25, step: 1,
          fmt: (v) => `${v.toFixed(0)}%`, maps: (v) => `h −= 0.1 × (${v.toFixed(0)} − 2% target)` },
        { type: "range", key: "cred", label: "Central-bank credibility", min: 0, max: 1, step: 0.05,
          fmt: (v) => v.toFixed(2), maps: (v) => `h += 1.0 × ${v.toFixed(2)}` } ] },
      { title: "Fiscal policy", items: [
        { type: "range", key: "vat", label: "VAT change", min: -5, max: 10, step: 0.5,
          fmt: (v) => `${v > 0 ? "+" : ""}${v.toFixed(1)} pp`, maps: (v) => `h −= 0.05 × ${v.toFixed(1)}` } ] },
    ],
    overrides: (L) => [`fields.money_growth=${yamlNum(L.money, 0)}`, `fields.credibility=${yamlNum(L.cred, 2)}`,
      `fields.vat_change=${yamlNum(L.vat, 1)}`, `uncertainty.gamma=${yamlNum(L.gamma, 2)}`],
  },
  taxpayers: {
    tab: "Compliance",
    kicker: "Tax compliance",
    state1: "evading",
    baselineLabel: "no evaders",
    dek: "Twelve taxpayers on a lattice, three evading at the start: the Zaklan Ising model, made coherent. Audits and penalties add a compliance field; a higher tax rate pushes the other way.",
    mapping: [["J · ZZ", "social influence and conditional cooperation between neighbours"],
              ["h · Z", "tax morale + audit probability × penalty − 0.05 × (tax rate − 30%)"],
              ["Γ · X", "ambivalence"]],
    defaults: (s) => ({ audit: s.fields.audit_prob, penalty: s.fields.penalty, rate: s.fields.tax_rate, gamma: s.uncertainty.gamma }),
    groups: () => [
      { title: "Enforcement", items: [
        { type: "range", key: "audit", label: "Audit probability", min: 0, max: 0.3, step: 0.01,
          fmt: (v) => pct(v), maps: (v) => `h += ${v.toFixed(2)} × penalty` },
        { type: "range", key: "penalty", label: "Penalty", min: 0, max: 20, step: 1,
          fmt: (v) => `${v.toFixed(0)} periods`, maps: () => "periods of forced honesty (Zaklan's k)" } ] },
      { title: "Tax", items: [
        { type: "range", key: "rate", label: "Tax rate", min: 10, max: 60, step: 1,
          fmt: (v) => `${v.toFixed(0)}%`, maps: (v) => `h −= 0.05 × (${v.toFixed(0)} − 30)` } ] },
    ],
    overrides: (L) => [`fields.audit_prob=${yamlNum(L.audit, 2)}`, `fields.penalty=${yamlNum(L.penalty, 0, true)}`,
      `fields.tax_rate=${yamlNum(L.rate, 0)}`, `uncertainty.gamma=${yamlNum(L.gamma, 2)}`],
  },
};
const GAMMA = { type: "range", key: "gamma", label: "Transverse field Γ", min: 0, max: 1.5, step: 0.05,
  fmt: (v) => v.toFixed(2), ticks: ["0 · classical", "1.5"],
  maps: (v) => (v === 0 ? "every term commutes: nothing can move" : "the only non-commuting term") };

/* ---------------------------------------------------------------- state */
const S = { presets: null, scen: "banks", L: null, RL: null, resp: null, t: 0, req: 0, timer: null,
            playing: null, view: "dynamics" };

/* ---------------------------------------------------------------- levers */
function renderLevers() {
  const spec = S.presets[S.scen].spec;
  const host = $("#levers");
  host.innerHTML = "";
  const groups = [...SCEN[S.scen].groups(spec, S.L), { title: "Uncertainty", badge: "quantum", quantum: true, items: [GAMMA] }];
  for (const g of groups) {
    const box = html("section", `group${g.quantum ? " quantum" : ""}`);
    const t = html("h3", "group-title", g.title);
    if (g.badge) t.appendChild(html("span", "badge", g.badge));
    box.appendChild(t);
    for (const it of g.items) box.appendChild(renderLever(it));
    host.appendChild(box);
  }
}

function renderLever(it) {
  const wrap = html("div", "lever");
  const top = html("div", "lever-top");
  top.appendChild(html("span", "lever-label", it.label));
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
      it.ticks.forEach((x) => tk.appendChild(html("span", null, x)));
      wrap.appendChild(tk);
    }
  } else {
    const chips = html("div", "chips");
    it.options.forEach((name, i) => {
      const b = html("button", `chip ${it.type === "radio" ? "seed" : "bail"}`, name);
      b.setAttribute("aria-pressed", it.type === "radio" ? S.L[it.key] === i : S.L[it.key].includes(i));
      if ((it.disabled || []).includes(i)) b.disabled = true;
      b.onclick = () => {
        if (it.type === "radio") { S.L[it.key] = i; S.L.bail = S.L.bail.filter((x) => x !== i); }
        else {
          const s = new Set(S.L[it.key]);
          s.has(i) ? s.delete(i) : s.add(i);
          S.L[it.key] = [...s].sort((a, c) => a - c);
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
function schedule() { clearTimeout(S.timer); S.timer = setTimeout(run, 140); }

async function run() {
  const id = ++S.req;
  const snap = JSON.parse(JSON.stringify(S.L));
  $("#main").classList.add("loading");
  progress(true);
  $("#engine").className = "engine busy";
  try {
    const res = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: S.scen, overrides: SCEN[S.scen].overrides(snap), exact: true }) });
    const data = await res.json();
    if (id !== S.req) return;
    if (!res.ok) throw new Error(data.error || res.statusText);
    S.resp = data;
    S.RL = snap;
    const y = data.result.series[data.result.headline];
    if (S.playing === null || S.t >= y.length) S.t = S.scen === "taxpayers" ? argmin(y) : argmax(y);
    render();
    $("#engine").className = "engine";
    $("#engine").textContent = `${data.result.summary.n} qubits · ${data.result.runtime_s.toFixed(2)} s`;
  } catch (err) {
    if (id !== S.req) return;
    $("#engine").className = "engine err";
    $("#engine").textContent = `error: ${err.message}`;
  } finally {
    if (id === S.req) { $("#main").classList.remove("loading"); progress(false); }
  }
}
function progress(on) {
  const p = $("#progress");
  if (on) { p.className = "progress"; void p.offsetWidth; p.className = "progress on"; }
  else p.className = "progress done";
}

/* ---------------------------------------------------------------- numbers */
function derived() {
  const { result: r, counterfactual: cf } = S.resp;
  const key = r.headline, y = r.series[key], base = r.baseline.series[key], times = r.times;
  const low = S.scen === "taxpayers";
  const iPeak = low ? argmin(y) : argmax(y);
  const cfy = cf ? cf.series[key] : null;
  return { r, cf, key, y, base, times, iPeak, low, peak: y[iPeak],
    basePeak: low ? min(base) : max(base), excess: y.map((v, i) => v - base[i]),
    cfy, cfPeak: cfy ? (low ? min(cfy) : max(cfy)) : null };
}

/* ---------------------------------------------------------------- intro + stats */
function renderIntro(D) {
  const sc = SCEN[S.scen], spec = S.presets[S.scen].spec, L = S.RL;
  $("#kicker").textContent = sc.kicker;
  $("#dek").textContent = sc.dek;
  const N = (x) => `<span class="fig-num">${x}</span>`;
  let h;
  if (S.scen === "banks") {
    const labels = spec.agents.labels, seed = labels[L.seed];
    const bail = L.bail.filter((b) => b !== L.seed).map((i) => labels[i]);
    const ratio = D.peak / Math.max(D.basePeak, 1e-9);
    if (L.gamma === 0) h = `With Γ = 0 every term commutes: ${seed} stays failed and no other bank moves.`;
    else if (bail.length && D.cf) h = `Bailing out ${list(bail)} holds peak insolvency to ${N(pct(D.peak))}, down from ${pct(D.cfPeak)}.`;
    else h = `When ${seed} fails, up to ${N(pct(D.peak))} of the banking system is insolvent${ratio > 1.25 ? `, ${ratio.toFixed(1)}× the background rate.` : ", barely above background noise."}`;
  } else if (S.scen === "firms") {
    const gap = D.peak - D.basePeak, m = L.money.toFixed(0);
    if (L.gamma === 0) h = "With Γ = 0 nothing moves: firms hold their prices whatever the central bank does.";
    else if (gap > 0.15) h = `At ${m}% money growth, expectations de-anchor: up to ${N(pct(D.peak))} of firms raise prices.`;
    else if (gap > 0.04) h = `At ${m}% money growth, up to ${N(pct(D.peak))} of firms raise prices, ${Math.round(gap * 100)} points above target.`;
    else h = `At ${m}% money growth, expectations stay anchored: at most ${N(pct(D.peak))} of firms raise prices.`;
  } else {
    if (L.gamma === 0) h = "With Γ = 0 nothing moves: the evaders stay evaders and everyone else stays honest.";
    else h = `With a ${pct(L.audit)} audit rate, compliance bottoms out at ${N(pct(D.peak))}${D.peak < D.y[0] - 0.03 ? " as the evaders pull their neighbours along." : "; the evaders stay contained."}`;
  }
  $("#headline").innerHTML = h;
}

function stat(label, value, note, cls = "") {
  const d = html("div", "stat");
  d.appendChild(html("div", "stat-label", label));
  const v = html("div", `stat-value ${cls}`);
  v.innerHTML = value;
  d.append(v, html("div", "stat-note", note));
  return d;
}
function renderStats(D) {
  const box = $("#stats");
  box.innerHTML = "";
  const spec = S.presets[S.scen].spec, L = S.RL;
  const big = (x) => `${Math.round(x * 100)}<small>%</small>`;
  const delta = (x, goodNeg = true) => [`${pts(x)}<small>pts</small>`,
    Math.abs(x) < 0.005 ? "" : (goodNeg ? x < 0 : x > 0) ? "delta-good" : "delta-bad"];
  const at = `at t = ${D.times[D.iPeak].toFixed(2)}`;
  if (S.scen === "banks") {
    box.appendChild(stat("Peak insolvent", big(D.peak), at));
    const ex = max(D.excess);
    box.appendChild(stat("Contagion", delta(ex, true)[0], "above the no-shock background", ex > 0.005 ? "delta-bad" : ""));
    const P = D.r.per_agent.p_one, B = D.r.baseline.per_agent.p_one;
    let best = 0, bestV = -1;
    for (let i = 0; i < D.r.graph.n; i++) {
      if (i === L.seed) continue;
      const v = max(P.map((row, k) => row[i] - B[k][i]));
      if (v > bestV) { bestV = v; best = i; }
    }
    box.appendChild(stat("Most exposed", spec.agents.labels[best],
      `${pct(max(P.map((r) => r[best])))} vs ${pct(max(B.map((r) => r[best])))} background`));
    if (D.cf) { const [v, c] = delta(D.peak - D.cfPeak, true); box.appendChild(stat("Bailout effect", v, "vs the same shock unchecked", c)); }
    else box.appendChild(stat("Bailout effect", `<span style="color:var(--muted)">—</span>`, "pick a bank to bail out"));
  } else if (S.scen === "firms") {
    box.appendChild(stat("Peak raising prices", big(D.peak), at));
    const [v, c] = delta(D.peak - D.basePeak, true);
    box.appendChild(stat("vs on-target economy", v, "peak, money growth at 2%", c));
    const half = D.y.findIndex((x) => x >= D.peak / 2);
    box.appendChild(stat("Time to half peak", `${D.times[Math.max(0, half)].toFixed(2)}<small>/J</small>`, "speed of propagation"));
    box.appendChild(stat("Neighbour agreement", D.r.series.synchronization[D.iPeak].toFixed(2), "⟨ZᵢZⱼ⟩ at the peak"));
  } else {
    box.appendChild(stat("Lowest compliance", big(D.peak), at));
    const [v, c] = delta(D.peak - D.basePeak, false);
    box.appendChild(stat("Cost of the evaders", v, "vs a lattice with none", c));
    box.appendChild(stat("Compliance at end", big(D.y[D.y.length - 1]), `t = ${D.times[D.times.length - 1].toFixed(1)}`));
    box.appendChild(stat("Neighbour agreement", D.r.series.synchronization[D.iPeak].toFixed(2), "⟨ZᵢZⱼ⟩ at the low point"));
  }
}

/* ---------------------------------------------------------------- dynamics: chart */
const CH = {};
function renderChart(D) {
  const host = $("#chart");
  host.innerHTML = "";
  const W = Math.max(320, host.clientWidth), H = 300;
  const m = { l: 40, r: 108, t: 10, b: 26 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b, T = D.times, tMax = T[T.length - 1];
  const x = (t) => m.l + (t / tMax) * iw;
  const y = (v) => m.t + (1 - v) * ih;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": D.r.headline_label }, host);
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    el("line", { x1: m.l, x2: m.l + iw, y1: y(v), y2: y(v), class: v === 0 ? "baseline-rule" : "gridline" }, svg);
    el("text", { x: m.l - 8, y: y(v) + 4, "text-anchor": "end", class: "tick-label" }, svg).textContent = `${v * 100}%`;
  }
  for (let t = 0; t <= tMax + 1e-9; t += tMax > 4 ? 1 : 0.5) {
    el("text", { x: x(t), y: H - 6, "text-anchor": "middle", class: "tick-label" }, svg).textContent = t.toFixed(0);
  }
  const sc = SCEN[S.scen];
  const series = [{ name: sc.baselineLabel, legend: sc.baselineLabel, data: D.base, color: COL.aqua, w: 2 }];
  if (D.cf) series.push({ name: "no bailout", legend: "same shock, no bailout", data: D.cfy, color: COL.orange, w: 2 });
  series.push({ name: "current", legend: "current policy", data: D.y, color: COL.blue, w: 2.75, main: true });
  const path = (d) => d.map((v, i) => `${i ? "L" : "M"}${x(T[i]).toFixed(1)},${y(v).toFixed(1)}`).join("");
  if (D.r.exact) el("path", { d: path(D.r.exact.series[D.key]), class: "series", stroke: COL.ink, "stroke-width": 1.25, "stroke-dasharray": "1.5 3.5", opacity: 0.6 }, svg);
  for (const s of series) el("path", { d: path(s.data), class: "series", stroke: s.color, "stroke-width": s.w }, svg);
  const hw = S.resp.hardware || [];
  for (const d of hw) {
    const ys = d.series[D.key], es = (d.stds || {})[D.key] || [];
    d.times.forEach((t, i) => {
      if (es[i]) el("line", { x1: x(t), x2: x(t), y1: y(ys[i] - es[i]), y2: y(ys[i] + es[i]), stroke: COL.yellow, "stroke-width": 1.5 }, svg);
      el("rect", { x: x(t) - 5, y: y(ys[i]) - 5, width: 10, height: 10, fill: COL.yellow, stroke: COL.surface, "stroke-width": 2, transform: `rotate(45 ${x(t)} ${y(ys[i])})` }, svg);
    });
  }
  const ends = series.map((s) => ({ s, yy: y(s.data[s.data.length - 1]) })).sort((a, b) => a.yy - b.yy);
  for (let i = 1; i < ends.length; i++) ends[i].yy = Math.max(ends[i].yy, ends[i - 1].yy + 15);
  for (const e of ends) {
    const t = el("text", { x: m.l + iw + 8, y: e.yy + 4, class: "end-label" }, svg);
    t.textContent = e.s.name;
    if (e.s.main) { t.style.fill = COL.ink; t.style.fontWeight = 600; }
  }
  const lg = $("#chart-legend");
  lg.innerHTML = "";
  const item = (color, label, cls = "") => {
    const sp = html("span"), i = html("i", cls);
    i.style.borderColor = color;
    sp.append(i, document.createTextNode(label));
    lg.appendChild(sp);
  };
  [...series].reverse().forEach((s) => item(s.color, s.legend));
  if (D.r.exact) item(COL.ink, "exact", "dot");
  for (const d of hw) item(COL.yellow, `${d.backend} (${d.kind.startsWith("noisy") ? "noisy sim" : "hardware"})`, "dia");
  $("#chart-title").textContent = D.r.headline_label.replace(/ \(.*\)/, "");
  const cursor = el("g", {}, svg);
  const line = el("line", { y1: m.t, y2: m.t + ih, class: "cursor-line" }, cursor);
  const dots = series.map((s) => el("circle", { r: 4.5, fill: s.color, class: "cursor-dot" }, cursor));
  const hit = el("rect", { x: m.l, y: m.t, width: iw, height: ih, class: "hit" }, svg);
  const idxAt = (ev) => {
    const r = svg.getBoundingClientRect();
    const t = ((((ev.clientX - r.left) / r.width) * W - m.l) / iw) * tMax;
    let best = 0;
    T.forEach((tt, i) => { if (Math.abs(tt - t) < Math.abs(T[best] - t)) best = i; });
    return best;
  };
  hit.addEventListener("mousemove", (ev) => {
    const i = idxAt(ev);
    setT(i);
    const rows = [...series].reverse().map((s) => [s.color, s.legend, pct(s.data[i], 1)]);
    if (D.r.exact) rows.push([COL.ink, "exact", pct(D.r.exact.series[D.key][i], 1)]);
    tooltip(ev, `t = ${T[i].toFixed(2)}`, rows);
  });
  hit.addEventListener("mouseleave", hideTooltip);
  Object.assign(CH, { x, y, T, line, dots, series });
}

/* ---------------------------------------------------------------- dynamics: network */
const NET = { nodes: [], labels: [] };
function renderNetwork(D) {
  const host = $("#network");
  host.innerHTML = "";
  const g = D.r.graph, n = g.n, L = S.RL;
  const W = Math.max(280, host.clientWidth), H = 296, pad = 36, R = n > 10 ? 18 : 20;
  const P = [...Array(n).keys()].map((i) => g.positions[i]);
  const xs = P.map((p) => p[0]), ys = P.map((p) => p[1]);
  const [x0, x1, y0, y1] = [min(xs), max(xs), min(ys), max(ys)];
  const sc = Math.min((W - 2 * pad) / Math.max(x1 - x0, 1e-9), (H - 2 * pad - 12) / Math.max(y1 - y0, 1e-9));
  const ox = (W - (x1 - x0) * sc) / 2, oy = (H - 12 - (y1 - y0) * sc) / 2;
  const px = (i) => ox + (g.positions[i][0] - x0) * sc;
  const py = (i) => oy + (y1 - g.positions[i][1]) * sc;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Agent network" }, host);
  const jmax = max(g.edges.map((e) => e[2])) || 1;
  for (const [i, j, J] of g.edges) {
    el("line", { x1: px(i), y1: py(i), x2: px(j), y2: py(j), class: "edge", "stroke-width": (0.8 + 4 * J / jmax).toFixed(2), opacity: (0.5 + 0.5 * J / jmax).toFixed(2) }, svg);
  }
  const bailed = S.scen === "banks" ? L.bail.filter((b) => b !== L.seed) : [];
  NET.nodes = []; NET.labels = [];
  for (let i = 0; i < n; i++) {
    const gx = px(i), gy = py(i);
    if (g.init_ones.includes(i)) el("circle", { cx: gx, cy: gy, r: R + 5, class: "ring-seed" }, svg);
    if (bailed.includes(i)) el("circle", { cx: gx, cy: gy, r: R + 5, class: "ring-bail" }, svg);
    const c = el("circle", { cx: gx, cy: gy, r: R, class: "node", fill: rampColor(D.r.per_agent.p_one[Math.min(S.t, D.times.length - 1)][i]), stroke: COL.surface, "stroke-width": 1.5 }, svg);
    const tx = el("text", { x: gx, y: gy + 0.5, class: "node-pct" }, svg);
    el("text", { x: gx, y: gy + R + 16, class: "node-label" }, svg).textContent = short(D.r.labels[i]);
    c.addEventListener("mousemove", (ev) => tooltip(ev, D.r.labels[i], [
      [null, `P(${SCEN[S.scen].state1})`, pct(D.r.per_agent.p_one[S.t][i], 1)], [null, "field h", g.h[i].toFixed(2)],
      [null, "Γ", g.gamma[i].toFixed(2)], [null, "links from shock", g.distance_from_seed[i]]]));
    c.addEventListener("mouseleave", hideTooltip);
    NET.nodes.push(c); NET.labels.push(tx);
  }
  $("#net-title").textContent = S.scen === "banks" ? "Bank network" : S.scen === "firms" ? "Supply grid" : "Taxpayer lattice";
  $("#net-legend").innerHTML = `<span>0</span><span class="bar"></span><span>100%</span>`;
  const foot = $("#net-foot");
  foot.innerHTML = "";
  const key = (color, label, dash) => {
    const sp = html("span"), i = html("i", dash ? "dash" : "");
    i.style.borderColor = color;
    sp.append(i, document.createTextNode(label));
    foot.appendChild(sp);
  };
  if (g.init_ones.length) key(COL.bad, S.scen === "banks" ? "failed bank" : "initial evaders");
  if (bailed.length) key(COL.aqua, "bailed out", true);
  foot.appendChild(html("span", null, `number = % ${SCEN[S.scen].state1} at the current time`));
  readTheme();
}

/* ---------------------------------------------------------------- light-cone */
const CONE = [];
function renderCone(D) {
  const host = $("#cone");
  host.innerHTML = "";
  CONE.length = 0;
  const sc = SCEN[S.scen];
  const panels = [{ title: "Current policy", color: COL.blue, P: D.r.per_agent.p_one }];
  panels.push(D.cf ? { title: "Same shock, no bailout", color: COL.orange, P: D.cf.per_agent.p_one }
                   : { title: `Comparison: ${sc.baselineLabel}`, color: COL.aqua, P: D.r.baseline.per_agent.p_one });
  const g = D.r.graph;
  const dist = g.distance_from_seed.map((d) => (d < 0 ? 99 : d));
  const order = [...Array(g.n).keys()].sort((a, b) => dist[a] - dist[b] || a - b);
  for (const pnl of panels) {
    const box = html("div");
    const t = html("p", "cone-title"), sw = html("i");
    sw.style.borderColor = pnl.color;
    t.append(sw, document.createTextNode(pnl.title));
    box.appendChild(t);
    host.appendChild(box);
    const W = Math.max(280, box.clientWidth), rowH = g.n > 10 ? 22 : 26, lw = 92;
    const H = rowH * g.n + 26, T = D.times, cw = (W - lw - 4) / T.length;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": pnl.title }, box);
    order.forEach((ag, row) => {
      const yy = row * rowH;
      el("text", { x: 0, y: yy + rowH / 2 + 4, class: "row-label" }, svg).textContent = short(D.r.labels[ag]);
      el("text", { x: lw - 8, y: yy + rowH / 2 + 4, "text-anchor": "end", class: "row-dist" }, svg).textContent = dist[ag] === 99 ? "" : `d${dist[ag]}`;
      T.forEach((tt, k) => {
        const p = pnl.P[k][ag];
        const c = el("rect", { x: lw + k * cw, y: yy + 1, width: Math.max(1, cw - 1.5), height: rowH - 2.5, rx: 2, fill: rampColor(p) }, svg);
        c.addEventListener("mousemove", (ev) => { setT(k); tooltip(ev, `${D.r.labels[ag]} · t = ${tt.toFixed(2)}`, [[null, `P(${sc.state1})`, pct(p, 1)]]); });
        c.addEventListener("mouseleave", hideTooltip);
      });
    });
    const tMax = T[T.length - 1];
    for (let tt = 0; tt <= tMax + 1e-9; tt += tMax > 4 ? 1 : 0.5) {
      el("text", { x: lw + (tt / tMax) * (T.length - 1) * cw + cw / 2, y: H - 6, "text-anchor": "middle", class: "tick-label" }, svg).textContent = tt.toFixed(0);
    }
    const cur = el("rect", { y: -2, width: cw + 0.5, height: rowH * g.n + 3, fill: "none", stroke: COL.ink, "stroke-width": 1.25, rx: 3 }, svg);
    CONE.push({ cur, lw, cw });
  }
  $("#cone-legend").innerHTML = `<span>0</span><span class="bar"></span><span>100% ${sc.state1}</span>`;
  readTheme();
}

/* ---------------------------------------------------------------- model */
function renderModel(D) {
  const map = $("#mapping");
  map.innerHTML = "";
  for (const [k, v] of SCEN[S.scen].mapping) map.append(html("dt", null, k), html("dd", null, v));
  const s = D.r.summary, facts = $("#facts");
  facts.innerHTML = "";
  const add = (k, v, note) => {
    const dd = html("dd", null, v);
    if (note) dd.appendChild(html("small", null, note));
    facts.append(html("dt", null, k), dd);
  };
  add("qubits", `${s.n}`, "one per agent");
  add("couplings", `${s.edges}`, "ZZ terms");
  add("exact memory", humanBytes(s.statevector_bytes), "16 · 2ⁿ bytes: doubles with every agent");
  add("gates / step", `~${s.cx_per_step} CX`, "linear in couplings, before routing");
  add("Trotter steps", `${s.trotter_steps_at_t_max}`, `first order (= second order for these observables), at t = ${D.times[D.times.length - 1]}`);
  if (D.r.trotter_max_error !== undefined) add("max error", D.r.trotter_max_error.toExponential(1), "circuit vs exact matrix exponential");
  for (const d of S.resp.hardware || []) add("device run", d.backend, `${d.kind}; ${(d.circuit_stats || []).map((x) => x.two_qubit_gates).join(" / ")} two-qubit gates`);
  const src = $("#sources");
  src.innerHTML = "";
  for (const [k, v] of Object.entries(D.r.sources || {})) {
    const li = html("li");
    li.append(html("b", null, k), document.createTextNode(v));
    src.appendChild(li);
  }
}

/* ---------------------------------------------------------------- views + clock */
function setView(v) {
  S.view = v;
  document.querySelectorAll("#views button").forEach((b) => b.setAttribute("aria-selected", b.dataset.v === v));
  for (const name of ["dynamics", "cone", "model"]) $(`#view-${name}`).hidden = name !== v;
  if (S.resp) renderView();
}
function renderView() {
  const D = NET.D;
  CONE.length = 0; NET.nodes = []; NET.labels = []; CH.line = null;
  if (S.view === "dynamics") { renderChart(D); renderNetwork(D); }
  else if (S.view === "cone") renderCone(D);
  else renderModel(D);
  setT(Math.min(S.t, D.times.length - 1));
}
function render() {
  const D = derived();
  NET.D = D;
  renderIntro(D);
  renderStats(D);
  $("#time").max = D.times.length - 1;
  renderView();
}
function setT(i) {
  if (!S.resp) return;
  S.t = i;
  const r = NET.D.r;
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
  S.playing = setInterval(() => { if (S.t >= T - 1) { togglePlay(); return; } setT(S.t + 1); }, 110);
}

/* ---------------------------------------------------------------- tooltip */
function tooltip(ev, head, rows) {
  const tt = $("#tooltip");
  tt.innerHTML = "";
  tt.appendChild(html("div", "tt-head", head));
  for (const [color, k, v] of rows) {
    const row = html("div", "tt-row"), left = html("span");
    if (color) { const sw = html("i", "sw"); sw.style.background = color; left.appendChild(sw); }
    left.appendChild(document.createTextNode(k));
    row.append(left, html("b", null, String(v)));
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
function closeSheet() { $("#sheet").classList.remove("open"); $("#sheet").setAttribute("aria-hidden", "true"); }
async function runYaml() {
  const out = $("#validator");
  out.innerHTML = '<span style="color:var(--muted)">validating…</span>';
  const res = await fetch("/api/run_yaml", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ yaml: $("#yaml").value }) });
  const d = await res.json();
  out.innerHTML = "";
  if (d.ok) out.appendChild(html("div", "ok", `✓ Valid. Compiled ${d.n} qubits and simulated: ${d.headline.replace(/_/g, " ")} reaches ${pct(d.peak)}.`));
  else {
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
  document.querySelectorAll("#scenarios button").forEach((b) => b.setAttribute("aria-selected", b.dataset.s === name));
  if (S.playing !== null) togglePlay();
  renderLevers();
  run();
}
async function boot() {
  readTheme();
  S.presets = await (await fetch("/api/presets")).json();
  for (const [k, sc] of Object.entries(SCEN)) {
    const b = html("button", null, sc.tab);
    b.dataset.s = k;
    b.setAttribute("role", "tab");
    b.onclick = () => selectScenario(k);
    $("#scenarios").appendChild(b);
  }
  document.querySelectorAll("#views button").forEach((b) => (b.onclick = () => setView(b.dataset.v)));
  $("#theme").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  const terms = $("#show-terms");
  terms.checked = localStorage.getItem("qecon-terms") === "1";
  $(".rail").classList.toggle("terms-on", terms.checked);
  terms.onchange = () => { $(".rail").classList.toggle("terms-on", terms.checked); localStorage.setItem("qecon-terms", terms.checked ? "1" : "0"); };
  $("#reset").onclick = () => { S.L = SCEN[S.scen].defaults(S.presets[S.scen].spec); renderLevers(); run(); };
  $("#play").onclick = togglePlay;
  $("#time").addEventListener("input", (e) => setT(+e.target.value));
  $("#open-spec").onclick = openSheet;
  $("#close-spec").onclick = closeSheet;
  $("#sheet").addEventListener("click", (e) => { if (e.target.id === "sheet") closeSheet(); });
  $("#run-yaml").onclick = runYaml;
  $("#reset-yaml").onclick = () => { $("#yaml").value = S.presets[S.scen].yaml; $("#validator").innerHTML = ""; };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSheet();
    if (["TEXTAREA", "INPUT"].includes(e.target.tagName)) return;
    if (e.key === " ") { e.preventDefault(); togglePlay(); }
    if (e.key === "ArrowRight" && S.resp) setT(Math.min(S.t + 1, S.resp.result.times.length - 1));
    if (e.key === "ArrowLeft" && S.resp) setT(Math.max(S.t - 1, 0));
  });
  let rz;
  addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => S.resp && renderView(), 120); });
  selectScenario("banks");
}
boot();
