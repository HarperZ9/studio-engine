"""Corpus novelty: fresh corpus is fully novel; adding a vector collapses its novelty.

Uses a real tempfile path (cleaned up) to exercise the JSON-backed persistence path.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from studio_engine.corpus import Corpus


def _features(**over) -> dict:
    base = {
        "coverage": 0.5,
        "centroid_offset": 0.3,
        "contrast": 0.4,
        "entropy": 0.8,
        "hue": 0.2,
    }
    base.update(over)
    return base


class TestCorpusNovelty(unittest.TestCase):
    def test_fresh_corpus_is_fully_novel(self):
        c = Corpus([])
        self.assertEqual(c.novelty(_features()), 1.0)

    def test_adding_same_features_drops_novelty_sharply(self):
        c = Corpus([])
        f = _features()
        self.assertEqual(c.novelty(f), 1.0)
        c.add(f)
        self.assertLess(c.novelty(f), 0.2)

    def test_identical_re_add_is_zero_distance(self):
        c = Corpus([])
        f = _features()
        c.add(f)
        self.assertAlmostEqual(c.novelty(f), 0.0, places=6)

    def test_far_features_stay_novel_after_add(self):
        c = Corpus([])
        c.add(_features(coverage=0.0, centroid_offset=0.0, contrast=0.0, entropy=0.0, hue=0.0))
        far = _features(coverage=1.0, centroid_offset=1.0, contrast=1.0, entropy=1.0, hue=1.0)
        # Opposite corner of the unit hypercube -> maximally novel.
        self.assertGreater(c.novelty(far), 0.9)

    def test_novelty_always_in_unit_interval(self):
        c = Corpus([])
        c.add(_features())
        for cov in (0.0, 0.25, 0.5, 0.75, 1.0):
            n = c.novelty(_features(coverage=cov))
            self.assertGreaterEqual(n, 0.0)
            self.assertLessEqual(n, 1.0)

    def test_len_tracks_vector_count(self):
        c = Corpus([])
        self.assertEqual(len(c), 0)
        c.add(_features())
        c.add(_features(coverage=0.9))
        self.assertEqual(len(c), 2)


class TestCorpusPersistence(unittest.TestCase):
    def setUp(self):
        fd, name = tempfile.mkstemp(suffix=".json", prefix="studio_corpus_")
        os.close(fd)
        os.unlink(name)  # start absent; Corpus.add should create it
        self.path = Path(name)

    def tearDown(self):
        try:
            if self.path.exists():
                self.path.unlink()
        except OSError:
            pass

    def test_add_writes_file_and_load_round_trips(self):
        c = Corpus.load(self.path)
        self.assertEqual(len(c), 0)
        f = _features()
        c.add(f)
        self.assertTrue(self.path.exists())

        # Raw JSON is a list of vectors.
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIsInstance(raw, list)
        self.assertEqual(len(raw), 1)

        # Reloading sees the persisted vector -> the same features are no longer novel.
        reloaded = Corpus.load(self.path)
        self.assertEqual(len(reloaded), 1)
        self.assertLess(reloaded.novelty(f), 0.2)

    def test_load_none_path_is_empty_and_unpersisted(self):
        c = Corpus.load(None)
        self.assertEqual(len(c), 0)
        self.assertIsNone(c.path)
        c.add(_features())  # must not raise, must not create any file
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
