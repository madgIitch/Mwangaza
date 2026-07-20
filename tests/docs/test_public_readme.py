from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PublicReadmeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_required_public_sections_exist(self):
        for heading in (
            "Requirements", "Installation", "Offline demo", "Connected mode",
            "Architecture", "Technology stack", "Implemented today", "Testing and verification",
            "Configuration", "Limitations", "Responsible use", "Roadmap",
        ):
            self.assertIn(f"## {heading}", self.readme)

    def test_canonical_commands_and_safety_are_documented(self):
        for command in (
            "uv sync --extra dev --extra app", "npm ci", "scripts/reset_demo.py",
            "scripts/demo_somalia.py", "scripts/demo_kenya.py", "MWANGAZA_MODE=\"demo\"",
            "npm run dev:api", "npm run lint", "npm run typecheck", "npm test", "npm run build",
        ):
            self.assertIn(command, self.readme)
        self.assertIn("never to demo", self.readme)
        self.assertIn("not official", self.readme)

    def test_architecture_and_provenance_links_exist(self):
        self.assertIn("```mermaid", self.readme)
        for target in ("docs/ARCHITECTURE.md", "docs/data-provenance.md", "docs/security/threat-model.md"):
            self.assertTrue((ROOT / target).exists())
            self.assertIn(target, self.readme)


if __name__ == "__main__":
    unittest.main()
