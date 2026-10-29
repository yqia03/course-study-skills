"""Exercise the producer and consumer together using generated HTML."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "skills/learning-notes/scripts/build_textbook.py"
READER = ROOT / "skills/kill-your-quizs/scripts/read_textbook.py"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.scope = Path(temporary.name) / "lecture5"
        work = self.scope / ".study-work"
        work.mkdir(parents=True)
        (self.scope / "lecture.txt").write_text("P(A|B) = P(A and B)/P(B), P(B)>0.\n")
        (work / "body.html").write_text(
            '<h2 id="probability">Probability（概率）</h2><p>事件 A 与 B。</p>'
            '<h3 id="conditional" data-aliases="条件概率">Conditional probability</h3>'
            '<p>P(B)&gt;0 时用条件概率公式。</p>'
            '<p class="source">lecture.txt，第 1 行。</p>'
            '<h3 id="other">Other topic</h3><p>UNRELATED_TOPIC</p>', encoding="utf-8")
        (work / "catalog.json").write_text(json.dumps({
            "coverage": "partial", "limitations": ["Other topic has no source."],
            "sources": [{"path": "lecture.txt"}],
            "section_sources": {"index.html#conditional": ["lecture.txt"]},
        }))
        result = subprocess.run([
            sys.executable, str(BUILDER), "--scope-root", str(self.scope),
            "--body", str(work / "body.html"), "--title", "Probability",
            "--catalog", str(work / "catalog.json"),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def read(self, *args):
        result = subprocess.run([sys.executable, str(READER), "--scope-root", str(self.scope),
                                 *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_generated_index_drives_bounded_read_and_detects_changes(self):
        found = self.read("--query", "条件概率")
        self.assertEqual(found["total_matches"], 1)
        section = found["sections"][0]["section"]
        result = self.read("--section", section)
        self.assertEqual(result["freshness"]["state"], "current")
        self.assertIn("lecture.txt，第 1 行", result["text"])
        self.assertNotIn("UNRELATED_TOPIC", result["text"])
        self.assertNotIn("ln-search", result["text"])
        self.assertEqual(result["context"]["parent_h2"]["section"], "index.html#probability")
        (self.scope / "lecture.txt").write_text("Teacher correction.\n")
        changed = self.read("--section", section)
        self.assertEqual(changed["freshness"]["state"], "changed")
        self.assertEqual(changed["freshness"]["page"]["state"], "current")

    def test_book_remains_reusable_after_moving_scope(self):
        moved = self.scope.parent / "moved-course"
        shutil.move(str(self.scope), moved)
        self.scope = moved
        result = self.read("--section", "index.html#conditional")
        self.assertEqual(result["freshness"]["state"], "current")

    def test_unmapped_section_does_not_claim_verified_sources(self):
        result = self.read("--section", "index.html#other")
        self.assertEqual(result["freshness"]["state"], "unverified")


if __name__ == "__main__":
    unittest.main()
