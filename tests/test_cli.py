import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from asrp import cli


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs/examples/production-deployment.v1.json"


class CliTest(unittest.TestCase):
    def invoke(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_example_validates_and_inspects(self) -> None:
        code, stdout, stderr = self.invoke(["validate", str(EXAMPLE)])
        self.assertEqual(code, 0, stderr)
        self.assertTrue(json.loads(stdout)["valid"])
        code, stdout, stderr = self.invoke(["inspect", str(EXAMPLE)])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["structure_id"], "STR-PRODUCTION-DEPLOYMENT")

    def test_compile_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            base = [
                "compile",
                str(EXAMPLE),
                "--scope",
                "production deployments",
                "--entry-point",
                "production-deployment",
                "--as-of",
                "2026-10-02T14:00:00Z",
            ]
            code, _, stderr = self.invoke([*base, "--output", str(first)])
            self.assertEqual(code, 0, stderr)
            code, _, stderr = self.invoke([*base, "--output", str(second)])
            self.assertEqual(code, 0, stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            manifest = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], cli.MANIFEST_SCHEMA_VERSION)
            self.assertEqual(len(manifest["evidence_requirements"]), 1)

    def test_tamper_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            record["integrity"]["record_fingerprint"] = cli.fingerprint(record)
            path = Path(directory) / "structure.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            code, _, stderr = self.invoke(["validate", str(path)])
            self.assertEqual(code, 0, stderr)
            record["description"] = "changed"
            path.write_text(json.dumps(record), encoding="utf-8")
            code, _, stderr = self.invoke(["validate", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("fingerprint mismatch", stderr)

    def test_artifact_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "architecture/model.json"
            artifact.parent.mkdir()
            artifact.write_text('{"components":[]}\n', encoding="utf-8")
            record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            record["artifacts"] = [
                {
                    "name": "Architecture",
                    "path": "architecture/model.json",
                    "media_type": "application/json",
                    "digest": cli.digest_file(artifact),
                    "role": "architecture",
                }
            ]
            record["elements"][0]["artifact_refs"] = ["architecture/model.json"]
            record["integrity"]["record_fingerprint"] = cli.fingerprint(record)
            path = root / "structure.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            code, stdout, stderr = self.invoke(
                ["verify", str(path), "--artifact-root", str(root)]
            )
            self.assertEqual(code, 0, stderr)
            self.assertTrue(json.loads(stdout)["valid"])
            artifact.write_text('{"components":["changed"]}\n', encoding="utf-8")
            code, _, stderr = self.invoke(
                ["verify", str(path), "--artifact-root", str(root)]
            )
            self.assertEqual(code, 2)
            self.assertIn("artifact verification failed", stderr)


if __name__ == "__main__":
    unittest.main()
