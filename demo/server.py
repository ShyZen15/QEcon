"""QEcon demo server: the web front end in demo/web/ talks to run_spec over a tiny JSON API.

    python -m demo.server              # -> http://localhost:8501
    python -m demo.server --port 9000

Standard library only (no Flask). demo/streamlit_app.py calls api_run too, so both demos
share one path. Everything runs on the local statevector simulator, so the demo cannot
fail on stage. Hardware points (results/hardware/*.json) are attached to a run when their
spec hash matches the current settings.
"""
import argparse
import json
import mimetypes
import os
import sys
import threading
import traceback
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import yaml  # noqa: E402

from qecon.api import physics_hash, run_spec  # noqa: E402
from qecon.spec import SpecError, load_spec  # noqa: E402

WEB = os.path.join(ROOT, "demo", "web")
HW_DIR = os.path.join(ROOT, "results", "hardware")
SPECS = {"banks": "specs/banks.yaml", "firms": "specs/firms.yaml",
         "taxpayers": "specs/taxpayers.yaml"}
_lock = threading.Lock()     # qiskit/numpy are fine threaded, but keep runs serial & cached


def base_spec(preset):
    s = load_spec(os.path.join(ROOT, SPECS[preset]))
    s.pop("_path", None)
    return s


def counterfactual_overrides(preset, overrides):
    """Banks with a bailout: compare against the same shock without the bailout."""
    if preset == "banks":
        for o in overrides:
            k, _, v = o.partition("=")
            if k == "fields.bailout.nodes" and yaml.safe_load(v):
                return [x for x in overrides if not x.startswith("fields.bailout.nodes=")] \
                    + ["fields.bailout.nodes=[]"], "same shock, no bailout"
    return None, None


@lru_cache(maxsize=512)
def _run(preset, overrides_key, exact):
    overrides = list(json.loads(overrides_key))
    r = run_spec(base_spec(preset), overrides=overrides, baseline=True, exact=exact)
    r["spec_hash"] = physics_hash(r["spec"])
    return r


def hardware_for(result):
    out = []
    if not os.path.isdir(HW_DIR):
        return out
    for f in sorted(os.listdir(HW_DIR)):
        if not f.endswith(".json") or f.endswith(".pending.json"):
            continue
        try:
            with open(os.path.join(HW_DIR, f), encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("preset") == result["preset"] and d.get("spec_hash") == result["spec_hash"]:
            out.append({k: d[k] for k in ("backend", "kind", "times", "series", "stds",
                                          "ideal_same_circuit", "circuit_stats") if k in d})
    return out


def api_run(body):
    preset = body["preset"]
    overrides = [str(o) for o in body.get("overrides", [])]
    key = json.dumps(overrides)
    with _lock:
        r = _run(preset, key, bool(body.get("exact", True)))
        cf_over, cf_label = counterfactual_overrides(preset, overrides)
        cf = _run(preset, json.dumps(cf_over), False) if cf_over else None
    return {"result": r, "counterfactual": cf, "counterfactual_label": cf_label,
            "hardware": hardware_for(r)}


def api_run_yaml(body):
    try:
        spec = yaml.safe_load(body["yaml"])
    except yaml.YAMLError as e:
        return {"ok": False, "errors": [f"Not valid YAML: {e}"]}
    if not isinstance(spec, dict):
        return {"ok": False, "errors": ["The spec must be a mapping (key: value pairs)."]}
    try:
        with _lock:
            r = run_spec(spec)
    except SpecError as e:
        lines = str(e).splitlines()
        return {"ok": False, "title": lines[0], "errors": [x.strip(" -") for x in lines[1:]]}
    return {"ok": True, "headline": r["headline"],
            "peak": max(r["series"][r["headline"]]), "n": r["summary"]["n"]}


def api_presets():
    out = {}
    for p in SPECS:
        s = base_spec(p)
        out[p] = {"spec": s, "yaml": open(os.path.join(ROOT, SPECS[p]), encoding="utf-8").read()}
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/presets":
            return self._send(200, api_presets())
        if path == "/":
            path = "/index.html"
        full = os.path.normpath(os.path.join(WEB, path.lstrip("/")))
        if not full.startswith(WEB) or not os.path.isfile(full):
            return self._send(404, {"error": "not found"})
        with open(full, "rb") as fh:
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            return self._send(200, fh.read(), ctype + ("; charset=utf-8" if "text" in ctype or "javascript" in ctype else ""))

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/run":
                return self._send(200, api_run(body))
            if self.path == "/api/run_yaml":
                return self._send(200, api_run_yaml(body))
            return self._send(404, {"error": "not found"})
        except SpecError as e:
            return self._send(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"QEcon demo on http://localhost:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
