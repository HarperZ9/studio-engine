"""Contract coverage: the handoff types/openapi must list EVERY generator + the right schema.

This is the regression guard for the original wound this branch set out to kill -- `types.ts` had
listed 3 of 8 generators. If a generator is added to the engine but not the contract, this fails.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from studio_engine import engine

_ROOT = Path(__file__).resolve().parent.parent
_TYPES = (_ROOT / "handoff" / "types.ts").read_text(encoding="utf-8")
_OPENAPI_TEXT = (_ROOT / "handoff" / "openapi.json").read_text(encoding="utf-8")
_OPENAPI = json.loads(_OPENAPI_TEXT)


class TestContractCoverage(unittest.TestCase):
    def test_every_generator_in_types_ts(self):
        for g in engine.generators():
            self.assertIn(f'"{g}"', _TYPES, f"{g} missing from handoff/types.ts")

    def test_every_generator_in_openapi(self):
        for g in engine.generators():
            self.assertIn(f'"{g}"', _OPENAPI_TEXT, f"{g} missing from handoff/openapi.json")

    def test_schema_version_in_types(self):
        self.assertIn("studio-engine/2", _TYPES)

    def test_openapi_version(self):
        self.assertEqual(_OPENAPI.get("info", {}).get("version"), "0.2.0")

    def test_openapi_declares_new_endpoints(self):
        paths = _OPENAPI.get("paths", {})
        self.assertIn("/compose", paths)
        self.assertTrue(any("program" in p for p in paths), "no /scene/{id}/program path")


if __name__ == "__main__":
    unittest.main()
