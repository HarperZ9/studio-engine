from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SECRET_ASSIGNMENT = re.compile(
    r"""
    (?<![A-Za-z0-9_])
    ["']?
    (?P<name>
        api[_-]?key|
        api[_-]?token|
        access[_-]?token|
        auth[_-]?token|
        client[_-]?secret|
        password|
        passwd|
        secret|
        token
    )
    ["']?
    \s*(?:=|:)\s*
    ["']?
    (?P<value>[A-Za-z0-9][A-Za-z0-9._~+/=-]{15,})
    ["']?
    """,
    re.IGNORECASE | re.VERBOSE,
)
PLACEHOLDER_TERMS = ("placeholder", "example", "sample", "dummy", "redacted", "<")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ForwardDeliveryContractTests(unittest.TestCase):
    def test_delivery_files_are_present(self) -> None:
        required = [
            "README.md",
            "USAGE.md",
            "CHANGELOG.md",
            "AUTHORS.md",
            "CONTRIBUTING.md",
            "LICENSE",
            "AGENTS.md",
            ".github/FUNDING.yml",
            ".github/workflows/ci.yml",
            "docs/brand/studio-engine-hero.png",
            "project-docs/specs/SPEC-studio-engine-forward-delivery.md",
        ]

        missing = [path for path in required if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_readme_serves_public_and_developer_audiences(self) -> None:
        text = read("README.md")

        for heading in ["## Try it", "## Why it matters", "## For developers"]:
            self.assertIn(heading, text)
        self.assertIn("docs/brand/studio-engine-hero.png", text)
        self.assertIn("replayable creative worlds", text.lower())
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("node --test showcase/tests/*.test.mjs", text)
        self.assertIn("USAGE.md", text)

    def test_changelog_and_usage_record_current_status(self) -> None:
        changelog = read("CHANGELOG.md")
        usage = read("USAGE.md")

        self.assertIn("Forward Delivery Contract", changelog)
        self.assertIn("Node 24-compatible", changelog)
        self.assertIn("SPEC-studio-engine-forward-delivery.md", changelog)
        self.assertIn("Generate A World", usage)
        self.assertIn("Verify Locally", usage)

    def test_docs_do_not_use_credential_shaped_assignments(self) -> None:
        docs = ["README.md", "USAGE.md", "CHANGELOG.md", "AGENTS.md"]
        findings: list[str] = []

        for path in docs:
            text = read(path)
            for match in SECRET_ASSIGNMENT.finditer(text):
                value = match.group("value").lower()
                if not any(term in value for term in PLACEHOLDER_TERMS):
                    line = text[: match.start()].count("\n") + 1
                    findings.append(f"{path}:{line}")

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
