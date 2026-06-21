"""Zero-dependency HTTP API for the studio-engine. Stdlib `http.server` only, CORS-open.

Endpoints (see handoff/ for the full contract):
  GET  /health                 -> {ok, service, version}
  GET  /generators             -> {generators: [...]}
  GET  /library                -> {organs: [...]}            the resource library
  GET  /gallery                -> {scenes: [summary...]}     pre-built showcase set
  POST /simulate {seed,generator,scheme} -> Scene            run the loop
  GET  /scene/{id}             -> Scene                      a cached scene
  GET  /audio/{id}.wav         -> audio/wav                  baked sonification of a scene

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
from urllib.parse import urlparse

from . import __version__
from .engine import simulate, library, generators
from .organs import sonify as snd

_SCENES: dict = {}   # id -> Scene
_GALLERY: list = []  # ordered scene ids


def _summary(scene) -> dict:
    return {
        "id": scene.id, "title": scene.title, "seed": scene.receipt.seed,
        "generator": scene.receipt.organ_ids[0], "score": scene.receipt.final_score,
        "converged": scene.trajectory.converged, "palette": scene.palette,
        "layers": [{"role": l.role, "organ_id": l.organ_id, "kind": l.artifact.kind,
                    "sha256": l.artifact.sha256} for l in scene.layers],
        "audio": (scene.audio.kind if scene.audio else None),
    }


def seed_gallery() -> None:
    if _GALLERY:
        return
    for g in generators():
        for seed in (7, 42):
            s = simulate(seed, generator=g)
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
        return self._send({"error": "not found", "path": path}, 404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/simulate":
            return self._send({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send({"error": "invalid json body"}, 400)
        try:
            s = simulate(seed=int(body.get("seed", 0)),
                         generator=str(body.get("generator", "phyllotaxis")),
                         scheme=str(body.get("scheme", "analogous")))
        except (ValueError, TypeError) as e:
            return self._send({"error": str(e)}, 400)
        _SCENES[s.id] = s
        return self._send(s.to_json())


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
