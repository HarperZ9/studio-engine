"""Zero-dependency HTTP API for the studio-engine. Stdlib `http.server` only, CORS-open.

Endpoints (see handoff/ for the full contract):
  GET  /health                 -> {ok, service, version}
  GET  /generators             -> {generators: [...]}
  GET  /library                -> {organs: [...]}            the resource library
  GET  /gallery                -> {scenes: [summary...]}     pre-built showcase set
  POST /simulate {seed,generator,scheme} -> World            run the loop
  POST /compose {seed,organs,scheme}     -> World            layered composite
  GET  /scene/{id}             -> World                      a cached World
  GET  /scene/{id}/program     -> {programs:[RenderProgram]} drop-in render programs per layer
  GET  /scene/{id}/filmstrip   -> per-step params for replaying convergence
  GET  /audio/{id}.wav         -> audio/wav                  baked sonification
  GET  /simulate/stream        -> SSE: 'step' events then 'world', then 'done'
  POST /session ... GET/POST /session/{id}/...              interactive cross-examine

The frontend "experience chamber" consumes these. Scenes carry a `params` layer (z=-1) the
chamber renders live; SVG/PNG layers are previews/fallbacks.
"""
from __future__ import annotations

import base64
import json
import re
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import __version__
from .engine import simulate, run, library, generators
from . import compose as comp
from .organs import sonify as snd
from .session import Session
from .model import _sha

_SCENES: dict = {}     # id -> Scene
_GALLERY: list = []    # ordered scene ids
_SESSIONS: dict = {}   # id -> Session (interactive cross-examine)


def _summary(world) -> dict:
    return {
        "id": world.id, "title": world.title, "seed": world.receipt.seed,
        "generator": world.receipt.organ_ids[0], "score": world.receipt.final_score,
        "converged": world.trajectory.converged, "palette": world.palette,
        "layers": [{"role": lyr.role, "organ_id": lyr.organ_id, "z": lyr.z, "blend": lyr.blend,
                    "target": lyr.render_program.target} for lyr in world.layers],
        "audio": (world.audio_program.waveform if world.audio_program else None),
        "animatable": bool(world.timeline),
    }


def seed_gallery() -> None:
    if _GALLERY:
        return
    for g in generators():
        for seed in (7, 42):
            # corpus_path=None: a deterministic, reproducible showcase gallery that does NOT mutate
            # the persistent corpus on startup. (On-demand POST /simulate still uses the living corpus.)
            s = simulate(seed, generator=g, corpus_path=None)
            _SCENES[s.id] = s
            _GALLERY.append(s.id)


class Handler(BaseHTTPRequestHandler):
    server_version = "studio-engine"

    def _send(self, obj, code: int = 200, ctype: str = "application/json") -> None:
        body = obj if isinstance(obj, (bytes, bytearray)) else json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, *a) -> None:  # quiet
        pass

    def do_OPTIONS(self) -> None:
        self._send(b"", 204)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/health"):
            return self._send({"ok": True, "service": "studio-engine", "version": __version__})
        if path == "/generators":
            return self._send({"generators": generators()})
        if path == "/library":
            return self._send({"organs": [asdict(o) for o in library()]})
        if path == "/gallery":
            return self._send({"scenes": [_summary(_SCENES[i]) for i in _GALLERY]})
        if path == "/simulate/stream":
            return self._stream(parse_qs(urlparse(self.path).query))
        m = re.match(r"^/scene/([0-9a-f]+)/filmstrip$", path)
        if m:
            s = _SCENES.get(m.group(1))
            if not s:
                return self._send({"error": "not found"}, 404)
            frames = [{"index": st.index, "phase": st.phase, "params": st.params,
                       "margins": st.margins, "score": st.score, "weakest": st.weakest}
                      for st in s.trajectory.steps]
            return self._send({"scene_id": s.id, "generator": s.receipt.organ_ids[0],
                               "palette": s.palette, "frames": frames})
        m = re.match(r"^/scene/([0-9a-f]+)/program$", path)
        if m:
            s = _SCENES.get(m.group(1))
            if not s:
                return self._send({"error": "not found"}, 404)
            return self._send({"scene_id": s.id,
                               "programs": [asdict(lyr.render_program) for lyr in s.layers]})
        m = re.match(r"^/scene/([0-9a-f]+)$", path)
        if m:
            s = _SCENES.get(m.group(1))
            return self._send(s.to_json() if s else {"error": "not found"}, 200 if s else 404)
        m = re.match(r"^/audio/([0-9a-f]+)\.wav$", path)
        if m:
            s = _SCENES.get(m.group(1))
            if not s:
                return self._send({"error": "not found"}, 404)
            scores = [st.score for st in s.trajectory.steps] or [s.receipt.final_score]
            wav = base64.b64decode(snd.sonify(s.receipt.seed, s.palette, scores).content)
            return self._send(wav, 200, "audio/wav")
        m = re.match(r"^/session/([0-9a-f]+)/explain$", path)
        if m:
            sess = _SESSIONS.get(m.group(1))
            if not sess:
                return self._send({"error": "not found"}, 404)
            return self._send(sess.explain(parse_qs(urlparse(self.path).query).get("axis", [None])[0]))
        m = re.match(r"^/session/([0-9a-f]+)$", path)
        if m:
            sess = _SESSIONS.get(m.group(1))
            return self._send(sess.state() if sess else {"error": "not found"}, 200 if sess else 404)
        return self._send({"error": "not found", "path": path}, 404)

    def _stream(self, q: dict) -> None:
        """Server-Sent Events: emit each refine step live, then the scene. The chamber
        watches the loop think in real time (the two-way telos, observed)."""
        seed = int((q.get("seed", ["0"])[0]) or 0)
        gen = q.get("generator", ["phyllotaxis"])[0]
        scheme = q.get("scheme", ["analogous"])[0]
        if gen not in generators():
            return self._send({"error": f"unknown generator {gen!r}"}, 400)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            for kind, obj in run(seed, gen, scheme=scheme):
                data = asdict(obj) if kind == "step" else obj.to_json()
                self.wfile.write(f"event: {kind}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"event: done\ndata: {}\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _body(self) -> dict | None:
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return None

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._body()
        if body is None:
            return self._send({"error": "invalid json body"}, 400)

        if path == "/simulate":
            try:
                s = simulate(seed=int(body.get("seed", 0)),
                             generator=str(body.get("generator", "phyllotaxis")),
                             scheme=str(body.get("scheme", "analogous")))
            except (ValueError, TypeError) as e:
                return self._send({"error": str(e)}, 400)
            _SCENES[s.id] = s
            return self._send(s.to_json())

        if path == "/compose":
            try:
                w = comp.compose(seed=int(body.get("seed", 0)),
                                 organ_set=body.get("organs") or body.get("organ_set"),
                                 scheme=str(body.get("scheme", "analogous")))
            except (ValueError, TypeError) as e:
                return self._send({"error": str(e)}, 400)
            _SCENES[w.id] = w
            return self._send(w.to_json())

        if path == "/session":
            try:
                sess = Session(seed=int(body.get("seed", 0)),
                               generator=str(body.get("generator", "phyllotaxis")),
                               scheme=str(body.get("scheme", "analogous")))
            except (ValueError, TypeError) as e:
                return self._send({"error": str(e)}, 400)
            sid = _sha(f"sess:{len(_SESSIONS)}:{body.get('seed', 0)}:{body.get('generator', '')}")
            _SESSIONS[sid] = sess
            return self._send({"session_id": sid, "state": sess.state()})

        m = re.match(r"^/session/([0-9a-f]+)/(step|inject)$", path)
        if m:
            sess = _SESSIONS.get(m.group(1))
            if not sess:
                return self._send({"error": "not found"}, 404)
            step = sess.step() if m.group(2) == "step" else sess.inject(body.get("params"))
            return self._send({"session_id": m.group(1), "step": step, "state": sess.state()})

        return self._send({"error": "not found", "path": path}, 404)


def serve(host: str = "127.0.0.1", port: int = 8777) -> None:
    seed_gallery()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"studio-engine API on http://{host}:{port}  (gallery: {len(_GALLERY)} scenes, "
          f"{len(generators())} generators)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    serve(port=int(sys.argv[1]) if len(sys.argv) > 1 else 8777)
