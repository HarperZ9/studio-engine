"""HTTP API: World responses, the render-program endpoint, and composition over the wire.

Runs the real Handler on an ephemeral port. /simulate is patched to skip the persistent corpus
so the test never mutates studio_engine/_corpus.json.
"""
from __future__ import annotations

import functools
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from studio_engine import server


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_simulate = server.simulate
        server.simulate = functools.partial(server.simulate, corpus_path=None)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        server.simulate = cls._orig_simulate

    def _get(self, path):
        c = HTTPConnection("127.0.0.1", self.port)
        c.request("GET", path)
        r = c.getresponse()
        body = r.read()
        c.close()
        return r.status, body

    def _post(self, path, obj):
        c = HTTPConnection("127.0.0.1", self.port)
        c.request("POST", path, body=json.dumps(obj).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
        r = c.getresponse()
        body = r.read()
        c.close()
        return r.status, body

    def test_health(self):
        st, body = self._get("/health")
        self.assertEqual(st, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_generators_lists_ten(self):
        st, body = self._get("/generators")
        gens = json.loads(body)["generators"]
        self.assertIn("gyroid", gens)
        self.assertIn("moire", gens)

    def test_simulate_returns_world_then_program(self):
        st, body = self._post("/simulate", {"seed": 7, "generator": "gyroid"})
        self.assertEqual(st, 200)
        w = json.loads(body)
        self.assertEqual(w["schema_version"], "studio-engine/2")
        self.assertEqual(w["layers"][0]["role"], "render")
        sid = w["id"]
        st2, _ = self._get(f"/scene/{sid}")
        self.assertEqual(st2, 200)
        st3, b3 = self._get(f"/scene/{sid}/program")
        self.assertEqual(st3, 200)
        progs = json.loads(b3)["programs"]
        self.assertEqual(progs[0]["target"], "glsl-fragment")
        self.assertIn("field(", progs[0]["source"])

    def test_compose_returns_multilayer_world(self):
        st, body = self._post("/compose", {"seed": 7, "organs": ["gyroid", "phyllotaxis"]})
        self.assertEqual(st, 200)
        w = json.loads(body)
        self.assertEqual(len(w["layers"]), 2)
        self.assertIn("composition", w)

    def test_audio_wav_header(self):
        st, body = self._post("/simulate", {"seed": 1, "generator": "flowfield"})
        sid = json.loads(body)["id"]
        st2, wav = self._get(f"/audio/{sid}.wav")
        self.assertEqual(st2, 200)
        self.assertTrue(wav.startswith(b"RIFF"))

    def test_unknown_scene_404(self):
        st, _ = self._get("/scene/deadbeef/program")
        self.assertEqual(st, 404)


if __name__ == "__main__":
    unittest.main()
