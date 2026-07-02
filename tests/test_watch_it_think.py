"""Wave-2 "watch it think" feature: end-to-end over the HTTP wire.

Covers the two can-it-FAIL catches from the UI's perspective:
  1. The SSE trajectory the operator watches matches the persisted (witnessed) record.
  2. A steered parameter the session rejects (clamps) is surfaced in the inject
     response, not silently applied.

`server.run`/`server.simulate` are patched to the corpus-free form so the suite
stays reproducible and never mutates studio_engine/_corpus.json.
"""
from __future__ import annotations

import functools
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from studio_engine import server


class TestWatchItThink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_run = server.run
        cls._orig_sim = server.simulate
        server.run = functools.partial(server.run, corpus_path=None)
        server.simulate = functools.partial(server.simulate, corpus_path=None)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        server.run = cls._orig_run
        server.simulate = cls._orig_sim

    def _post(self, path, obj):
        c = HTTPConnection("127.0.0.1", self.port)
        c.request("POST", path, body=json.dumps(obj).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
        r = c.getresponse()
        body = json.loads(r.read())
        c.close()
        return r.status, body

    def _get(self, path):
        c = HTTPConnection("127.0.0.1", self.port)
        c.request("GET", path)
        r = c.getresponse()
        body = r.read().decode("utf-8")
        c.close()
        return r.status, body

    def test_sse_stream_matches_persisted_trajectory(self):
        """CAN-IT-FAIL #1 (UI variant): watch the stream, then re-check the record."""
        _, body = self._get("/simulate/stream?seed=99&generator=gyroid&scheme=analogous")
        steps, world = [], None
        lines = body.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("event: step") and i + 1 < len(lines):
                steps.append(json.loads(lines[i + 1][len("data: "):]))
            elif line.startswith("event: world") and i + 1 < len(lines):
                world = json.loads(lines[i + 1][len("data: "):])
        self.assertIsNotNone(world)

        st, sbody = self._get(f"/scene/{world['id']}")
        self.assertEqual(st, 200)
        persisted = json.loads(sbody)["trajectory"]["steps"]
        self.assertEqual(len(steps), len(persisted))
        for i, (s, p) in enumerate(zip(steps, persisted)):
            self.assertEqual(s["margins"], p["margins"], f"step {i}: margins diverge")

    def test_inject_rejection_surfaced_over_wire(self):
        """CAN-IT-FAIL #2: POST /session/{id}/inject with an out-of-bounds param
        returns a step whose `rejected` map names the clamped param."""
        st, sess = self._post("/session", {"seed": 7, "generator": "gyroid"})
        self.assertEqual(st, 200)
        sid = sess["session_id"]

        st, result = self._post(f"/session/{sid}/inject", {"params": {"freq": 999.0}})
        self.assertEqual(st, 200)
        step = result["step"]
        self.assertIn("rejected", step)
        self.assertIn("freq", step["rejected"])
        user_val, clamped_val = step["rejected"]["freq"]
        self.assertEqual(user_val, 999.0)
        self.assertLessEqual(clamped_val, 10.0)

    def test_inject_in_bounds_no_rejection_over_wire(self):
        """An in-bounds steer returns an empty (or absent) rejected map."""
        st, sess = self._post("/session", {"seed": 7, "generator": "gyroid"})
        sid = sess["session_id"]
        st, result = self._post(f"/session/{sid}/inject", {"params": {"freq": 6.0}})
        self.assertEqual(st, 200)
        self.assertEqual(result["step"].get("rejected", {}), {})

    def test_session_state_exposes_bounds(self):
        """The slider panel builds one slider per param from state.bounds."""
        st, sess = self._post("/session", {"seed": 7, "generator": "gyroid"})
        self.assertIn("bounds", sess["state"])
        self.assertIn("freq", sess["state"]["bounds"])


if __name__ == "__main__":
    unittest.main()
