import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/learning-notes/scripts/inventory_materials.py"
SPEC = importlib.util.spec_from_file_location("inventory_materials", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.scope = self.parent / "lecture5"
        self.scope.mkdir()
        (self.scope / "lecture.txt").write_text("course material", encoding="utf-8")

    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.scope), *map(str, arguments)],
                              capture_output=True, text=True)

    def test_nested_manifest_and_stdout(self):
        output = self.scope / "textbook/work/materials.json"
        result = self.run_cli("--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(manifest["candidate_files"], 1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["generated_by"], MODULE.GENERATED_BY)

    def test_function_rejects_outside_output_and_root(self):
        for output in (self.parent / "materials.json", self.scope / "../escape.json", self.scope):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "inside the material root"):
                MODULE.inventory(self.scope, output=output)

    def test_cli_rejects_symlink_parent_escape_without_writing(self):
        outside = self.parent / "other"
        outside.mkdir()
        (self.scope / "link").symlink_to(outside, target_is_directory=True)
        result = self.run_cli("--output", self.scope / "link/materials.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside the material root", result.stderr)
        self.assertFalse((outside / "materials.json").exists())

    def test_overwrite_cannot_replace_original_files(self):
        for name, content in (("lecture.txt", "course material"),
                              ("original.json", '{"topic": "lecture"}'),
                              ("array.json", '[]')):
            output = self.scope / name
            output.write_text(content, encoding="utf-8")
            with self.subTest(name=name):
                result = self.run_cli("--output", output, "--overwrite")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("original file", result.stderr)
                self.assertEqual(output.read_text(encoding="utf-8"), content)

    def test_generated_manifest_requires_explicit_overwrite(self):
        output = self.scope / "materials.json"
        self.assertEqual(self.run_cli("--output", output).returncode, 0)
        previous = output.read_text(encoding="utf-8")
        (self.scope / "extra.txt").write_text("new material", encoding="utf-8")
        result = self.run_cli("--output", output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(encoding="utf-8"), previous)
        result = self.run_cli("--output", output, "--overwrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(manifest["candidate_files"], 2)
        self.assertEqual(next(record for record in manifest["records"]
                              if record["path"] == "materials.json")["status"], "excluded")


if __name__ == "__main__":
    unittest.main()
