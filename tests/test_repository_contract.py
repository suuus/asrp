import json
import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTest(unittest.TestCase):
    def test_versions_match(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".github/plugin/marketplace.json").read_text(encoding="utf-8"))
        cli_text = (ROOT / "src/asrp/cli.py").read_text(encoding="utf-8")
        version = re.search(r'^VERSION = "([^"]+)"$', cli_text, re.MULTILINE)
        self.assertIsNotNone(version)
        expected = project["project"]["version"]
        self.assertEqual(plugin["version"], expected)
        self.assertEqual(marketplace["metadata"]["version"], expected)
        self.assertEqual(version.group(1), expected)

    def test_skills_and_links(self) -> None:
        expected = {"asrp-write", "asrp-bind", "asrp-resolve", "asrp-compile", "asrp-verify"}
        actual = {path.parent.name for path in (ROOT / ".github/skills").glob("*/SKILL.md")}
        self.assertEqual(actual, expected)
        missing = []
        for path in [ROOT / "README.md", *ROOT.joinpath("docs").rglob("*.md")]:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                local = target.split("#", 1)[0]
                if local and not (path.parent / local).resolve().exists():
                    missing.append(f"{path.relative_to(ROOT)}: {target}")
        self.assertEqual(missing, [])

    def test_json_files_parse(self) -> None:
        for path in [
            ROOT / "schemas/ape-structure-record-v1.schema.json",
            ROOT / "schemas/isee-execution-manifest-v1.schema.json",
            ROOT / "docs/examples/production-deployment.v1.json",
            ROOT / "plugin.json",
            ROOT / ".github/plugin/marketplace.json",
        ]:
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
