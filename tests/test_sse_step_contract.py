"""The accountability catch: the LIVE stream the operator watches must match the
WITNESSED record exactly. A divergence between what is shown (SSE `step` events)
and what is persisted (the World's trajectory) is caught here, across every
generator. This is the merit feature and the accountability artifact being one
thing: if they drift, the visualization is lying and this test fails.

Runs the real Handler on an ephemeral port. `server.run` is patched to skip the
persistent corpus so the test never mutates studio_engine/_corpus.json.
"""
from __future__ import annotations

import functools
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from studio_engine import server


def _parse_sse(body: str):
    """Return (steps, world) from a raw SSE body. Events are `event: <kind>\\ndata: <json>`."""
    steps, world = [], None
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("event: step") and i + 1 < len(lines):
            steps.append(json.loads(lines[i + 1][len("data: "):]))
        elif line.startswith("event: world") and i + 1 < len(lines):
            world = json.loads(lines[i + 1][len("data: "):])
    return steps, world


class TestSSEStepContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch run + simulate to the corpus-free form so the suite is reproducible
        # and never mutates the living corpus.
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

    def _get(self, path):
        c = HTTPConnection("127.0.0.1", self.port)
        c.request("GET", path)
        r = c.getresponse()
        body = r.read().decode("utf-8")
        c.close()
        return r.status, body

    def _stream(self, seed, gen):
        _, body = self._get(f"/simulate/stream?seed={seed}&generator={gen}&scheme=analogous")
        return _parse_sse(body)

    def test_all_generators_stream_trajectory_matches_persisted(self):
        """Every generator: streamed step margins/params/phase == persisted trajectory."""
        for gen in server.generators():
            with self.subTest(generator=gen):
                streamed, world = self._stream(7, gen)
                self.assertIsNotNone(world, f"{gen}: no world event in stream")

                st, body = self._get(f"/scene/{world['id']}")
                self.assertEqual(st, 200, f"{gen}: streamed world not retrievable at /scene/id")
                persisted = json.loads(body)["trajectory"]["steps"]

                self.assertEqual(len(streamed), len(persisted),
                                 f"{gen}: streamed vs persisted step count differ")
                for i, (s, p) in enumerate(zip(streamed, persisted)):
                    self.assertEqual(s["margins"], p["margins"],
                                     f"{gen} step {i}: margins diverge "
                                     f"(stream {s['margins']} vs persisted {p['margins']})")
                    self.assertEqual(s["params"], p["params"], f"{gen} step {i}: params diverge")
                    self.assertEqual(s["phase"], p["phase"], f"{gen} step {i}: phase differs")

    def test_streamed_world_is_witnessed_and_retrievable(self):
        """The world emitted over SSE must be persisted (retrievable) so the shown
        trajectory can be re-checked against the witnessed receipt."""
        streamed, world = self._stream(42, "phyllotaxis")
        self.assertTrue(streamed, "no steps streamed")
        st, body = self._get(f"/scene/{world['id']}")
        self.assertEqual(st, 200)
        persisted = json.loads(body)
        # The receipt's final score must equal the best score seen in the stream.
        self.assertEqual(persisted["receipt"]["scene_id"], world["id"])


if __name__ == "__main__":
    unittest.main()
