import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/kill-your-quizs/scripts/read_textbook.py"
SPEC = importlib.util.spec_from_file_location("read_textbook", SCRIPT)
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


class ReadTextbookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.scope = Path(self.temp.name) / "course"
        self.book = self.scope / "textbook"
        self.book.mkdir(parents=True)
        self.source = self.scope / "lecture.txt"
        self.source.write_text("Verified lecture\n", encoding="utf-8")
        self.page = self.book / "page.html"
        self.page.write_text("""<!doctype html><html><head><style>CSS_SECRET</style>
<script>JS_SECRET</script></head><body>
<nav><a href="#topic">NAV_SECRET</a></nav>
<h2 id="topic">概率 Probability</h2>
<p>中文 English P(A) = 0.5.</p><style>BODY_CSS_SECRET</style>
<script>BODY_JS_SECRET</script><template>TEMPLATE_SECRET</template>
<p><math><mfrac><mi>a</mi><mi>b</mi></mfrac><mo>+</mo>
<msup><mi>x</mi><mn>2</mn></msup></math> and y<sub>i</sub>.</p>
<h3 id="child">Conditional probability</h3><p>Child content.</p>
<h3 id="other-child">Other child</h3><p>Sibling content.</p>
<h2 id="next">Next section</h2><p>NEXT_SECRET</p>
</body></html>""", encoding="utf-8")
        self.index = self.book / "textbook-index.json"
        self.data = {
            "schema_version": 1, "generated_by": "learning-notes",
            "entry": "page.html", "scope_root": "..", "coverage": "partial",
            "limitations": ["Only relevant lectures included."],
            "pages": [{"path": "page.html", "sha256": self.digest(self.page)}],
            "sources": [{"path": "lecture.txt", "sha256": self.digest(self.source)},
                        {"path": "irrelevant-missing.txt", "sha256": "0" * 64}],
            "sections": [
                {"path": "page.html", "anchor": "topic", "title": "概率 Probability",
                 "aliases": ["chance", "概率论"], "source_ids": [0]},
                {"path": "page.html", "anchor": "child", "title": "Conditional probability",
                 "aliases": ["条件概率"], "source_ids": [0]},
                {"path": "page.html", "anchor": "other-child", "title": "Other child",
                 "aliases": [], "source_ids": [1]},
            ]}
        self.save()

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def save(self):
        self.index.write_text(json.dumps(self.data), encoding="utf-8")

    def call(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = reader.main(["--scope-root", str(self.scope), *args])
        return status, json.loads(output.getvalue())

    def section(self, name="topic", *args):
        status, result = self.call("--section", "page.html#" + name, *args)
        self.assertEqual(status, 0, result)
        return result

    def split_layout(self):
        lecture = self.scope / "Lecture8"
        lecture.mkdir()
        self.book.rename(lecture / "textbook")
        self.source.rename(lecture / "lecture.txt")
        self.book = lecture / "textbook"
        self.page = self.book / "page.html"
        self.index = self.book / "textbook-index.json"
        self.source = lecture / "lecture.txt"
        work = self.scope / "problem_set_4"
        work.mkdir()
        return work, lecture

    def call_work(self, work, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = reader.main(["--work-root", str(work), *args])
        return status, json.loads(output.getvalue())

    def test_separate_work_and_course_reference_roots_read_without_writes(self):
        work, lecture = self.split_layout()
        # A same-named assignment file must not become the lecture source.
        (work / "lecture.txt").write_text("Assignment local file", encoding="utf-8")
        before = {str(p.relative_to(self.scope)): p.read_bytes()
                  for p in self.scope.rglob("*") if p.is_file()}
        status, result = self.call_work(
            work, "--reference-root", str(self.scope), "--index", str(self.index),
            "--section", "page.html#child")
        self.assertEqual(status, 0, result)
        self.assertEqual(result["freshness"]["state"], "current")
        self.assertEqual(result["work_root"], str(work.resolve()))
        self.assertEqual(result["reference_roots"], [str(self.scope.resolve())])
        self.assertEqual(result["material_root"], str(lecture.resolve()))
        self.assertEqual(result["source_locations"]["materials"], ["lecture.txt"])
        self.assertEqual(before, {str(p.relative_to(self.scope)): p.read_bytes()
                                  for p in self.scope.rglob("*") if p.is_file()})
        self.assertFalse((work / "textbook").exists())

    def test_reference_access_requires_explicit_root_and_does_not_search_parents(self):
        work, lecture = self.split_layout()
        self.assertIn("allowed read roots", self.call_work(
            work, "--index", str(self.index))[1]["error"])
        self.assertIn(str(work / "textbook" / "textbook-index.json"), self.call_work(
            work, "--reference-root", str(self.scope))[1]["error"])
        sibling = self.scope / "Lecture9"
        sibling.mkdir()
        self.assertEqual(self.call_work(
            work, "--reference-root", str(sibling), "--index", str(self.index))[0], 1)
        self.assertEqual(self.call_work(
            work, "--reference-root", str(sibling), "--reference-root", str(lecture),
            "--index", str(self.index))[0], 0)

    def test_index_metadata_cannot_expand_reference_access(self):
        work, lecture = self.split_layout()
        self.data["scope_root"] = "../.."
        self.save()
        status, result = self.call_work(work, "--reference-root", str(lecture),
                                        "--index", str(self.index))
        self.assertEqual(status, 1)
        self.assertIn("declared scope_root escapes allowed read roots", result["error"])

    def test_narrow_material_scope_confines_all_index_paths(self):
        work, lecture = self.split_layout()
        # The outer course is authorized, but a lecture index cannot reach siblings.
        for container, key in ((self.data, "entry"), (self.data["sections"][0], "path"),
                               (self.data["sources"][0], "path"),
                               (self.data["pages"][0], "path")):
            old = container[key]
            container[key] = "../../problem_set_4/outside.html"
            self.save()
            self.assertEqual(self.call_work(work, "--reference-root", str(self.scope),
                                            "--index", str(self.index))[0], 1)
            container[key] = old
        self.save()
        self.assertEqual(self.call_work(
            work, "--reference-root", str(self.scope), "--index", str(self.index),
            "--section", "../../problem_set_4/outside.html#x")[0], 1)

    def test_reference_index_page_and_source_symlink_escapes_rejected(self):
        work, lecture = self.split_layout()
        outside = self.scope / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        for target in (self.index, self.page, self.source):
            previous = target.read_bytes()
            target.unlink()
            target.symlink_to(outside)
            status, result = self.call_work(work, "--reference-root", str(lecture),
                                            "--index", str(self.index))
            self.assertEqual(status, 1, result)
            target.unlink()
            target.write_bytes(previous)

    def test_invalid_roots_and_mixed_root_modes_are_rejected(self):
        work, lecture = self.split_layout()
        for invalid in (self.scope / "missing", self.source):
            self.assertEqual(self.call_work(invalid)[0], 1)
            self.assertEqual(self.call_work(work, "--reference-root", str(invalid))[0], 1)
        self.assertEqual(self.call_work(work, "--scope-root", str(lecture))[0], 1)
        self.assertIn("cannot be combined", self.call(
            "--reference-root", str(lecture))[1]["error"])

    def test_default_index_inside_work_and_relative_explicit_index(self):
        status, result = self.call_work(self.scope, "--section", "page.html#child")
        self.assertEqual(status, 0, result)
        self.assertEqual(result["freshness"]["state"], "current")
        # Relative explicit indexes retain cwd semantics, even with another work root.
        work, lecture = self.split_layout()
        previous_cwd = Path.cwd()
        try:
            os.chdir(self.scope)
            status, result = self.call_work(work, "--reference-root", str(lecture),
                                            "--index", "Lecture8/textbook/textbook-index.json")
        finally:
            os.chdir(previous_cwd)
        self.assertEqual(status, 0, result)

    def test_read_chinese_english_math_and_h2_children(self):
        result = self.section()
        self.assertIn("中文 English", result["text"])
        self.assertIn("(a)/(b)", result["text"])
        self.assertIn("x^(2)", result["text"])
        self.assertIn("y_(i)", result["text"])
        self.assertIn("Child content", result["text"])
        self.assertIn("Sibling content", result["text"])
        self.assertNotIn("SECRET", result["text"])
        self.assertNotIn("Next section", result["text"])
        self.assertEqual(result["freshness"]["state"], "missing")
        self.assertEqual(result["source_ids"], [0])
        self.assertEqual(result["source_locations"]["materials"],
                         ["lecture.txt", "irrelevant-missing.txt"])
        self.assertEqual([s["section"] for s in result["included_sections"]],
                         ["page.html#topic", "page.html#child", "page.html#other-child"])
        self.assertGreater(result["source_locations"]["html"]["start_line"], 1)
        self.assertIsNotNone(result["source_locations"]["html"]["end_line"])
        self.assertEqual(result["trust"], "untrusted_data")

    def test_h3_stops_before_sibling_and_reports_parent(self):
        result = self.section("child")
        self.assertIn("Child content", result["text"])
        self.assertNotIn("Sibling content", result["text"])
        self.assertNotIn("中文", result["text"])
        self.assertEqual(result["freshness"]["state"], "current")
        self.assertEqual([s["section"] for s in result["included_sections"]], ["page.html#child"])
        self.assertEqual(result["context"]["parent_h2"],
                         {"title": "概率 Probability", "section": "page.html#topic"})

    def test_query_title_alias_only_and_catalog_no_content_reads(self):
        original_open = Path.open

        def guarded_open(path, *args, **kwargs):
            self.assertEqual(path, self.index.resolve(), f"Unnecessary content read: {path}")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", guarded_open):
            status, result = self.call("--query", "CHANCE")
            self.assertEqual(status, 0)
            self.assertEqual([s["section"] for s in result["sections"]], ["page.html#topic"])
            self.assertNotIn("text", result)
            self.assertEqual(self.call("--query", "Child content")[1]["total_matches"], 0)
            self.assertEqual(self.call("--query", "条件概率")[1]["total_matches"], 1)
            catalog = self.call("--max-results", "2")[1]
            self.assertEqual(catalog["mode"], "catalog")
            self.assertEqual(len(catalog["sections"]), 2)
            self.assertTrue(catalog["truncated"])

    def test_only_selected_sources_are_opened(self):
        original_open = Path.open

        def guarded_open(path, *args, **kwargs):
            self.assertNotEqual(path.name, "irrelevant-missing.txt")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", guarded_open):
            self.assertEqual(self.section("child")["freshness"]["state"], "current")

    def test_changed_missing_and_unverified_sources(self):
        self.source.write_text("Changed", encoding="utf-8")
        self.assertEqual(self.section("child")["freshness"]["state"], "changed")
        self.source.unlink()
        self.assertEqual(self.section("child")["freshness"]["state"], "missing")
        self.data["sections"][1]["source_ids"] = [200]
        self.save()
        self.assertEqual(self.section("child")["freshness"]["state"], "unverified")
        del self.data["sections"][1]["source_ids"]
        self.save()
        self.assertEqual(self.section("child")["freshness"]["state"], "unverified")

    def test_page_hash_changed_or_absent_is_not_current(self):
        self.page.write_text(self.page.read_text() + "<!--manual edit-->", encoding="utf-8")
        result = self.section("child")
        self.assertEqual(result["freshness"]["state"], "changed")
        self.assertEqual(result["freshness"]["sources"][0]["state"], "current")
        del self.data["pages"]
        self.save()
        self.assertEqual(self.section("child")["freshness"]["state"], "unverified")

    def test_no_index_has_useful_fallback(self):
        self.index.unlink()
        status, result = self.call()
        self.assertEqual(status, 1)
        self.assertIn("legacy HTML or raw course materials", result["error"])

    def test_scope_mismatch_and_traversal_rejected(self):
        self.data["scope_root"] = "."
        self.save()
        self.assertIn("does not equal", self.call()[1]["error"])
        self.data["scope_root"] = ".."
        for container, key in ((self.data, "entry"), (self.data["sections"][0], "path"),
                               (self.data["sources"][0], "path"),
                               (self.data["pages"][0], "path")):
            old = container[key]
            container[key] = "../../outside.html"
            self.save()
            self.assertEqual(self.call()[0], 1)
            container[key] = old
        self.save()
        self.assertEqual(self.call("--section", "../../outside.html#x")[0], 1)
        self.assertEqual(self.call("--index", str(self.scope.parent / "outside.json"))[0], 1)

    def test_page_source_and_index_symlink_escape_rejected(self):
        outside = self.scope.parent / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        for target in (self.page, self.source, self.index):
            previous = target.read_bytes()
            target.unlink()
            target.symlink_to(outside)
            self.assertEqual(self.call()[0], 1)
            target.unlink()
            target.write_bytes(previous)

    def test_text_limit_exact_lookup_and_missing_anchor(self):
        result = self.section("topic", "--max-chars", "40")
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["text"]), 40)
        self.assertEqual(result["freshness"]["state"], "current")
        self.assertEqual([s["section"] for s in result["included_sections"]], ["page.html#topic"])
        self.assertEqual(self.call("--section", "page.html#unknown")[0], 1)
        self.data["sections"][0]["anchor"] = "absent"
        self.save()
        self.assertIn("not found", self.call("--section", "page.html#absent")[1]["error"])

    def test_mathml_tex_annotation_and_hidden_duplicates(self):
        self.page.write_text('''<h2 id="topic">Math</h2>
<math><semantics><mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow>
<annotation encoding="application/x-tex">x + y</annotation></semantics></math>
<span aria-hidden="true">HIDDEN_SECRET</span><h2>Next</h2>''', encoding="utf-8")
        result = self.section()
        self.assertEqual(result["text"].count("x + y"), 1)
        self.assertNotIn("SECRET", result["text"])

    def test_section_wrapper_ends_before_unrelated_prose(self):
        self.page.write_text('''<section id="topic"><h2>Selected</h2>
<p>Inside.</p><h3>Child</h3><p>Included.</p></section>
<p>UNRELATED_SECRET</p><h2>Next</h2>''', encoding="utf-8")
        result = self.section()
        self.assertIn("Included.", result["text"])
        self.assertNotIn("SECRET", result["text"])

    def test_unmapped_included_heading_is_unverified(self):
        self.data["sections"].pop()
        self.save()
        result = self.section()
        self.assertEqual(result["freshness"]["state"], "unverified")
        self.assertEqual(result["included_sections"][-1]["mapping"], "unverified")
        self.assertEqual(result["included_sections"][-1]["section"], "page.html#other-child")
        self.assertEqual(result["source_locations"]["materials"], ["lecture.txt"])
        self.assertEqual(self.section("child")["freshness"]["state"], "current")

    def test_included_child_without_sources_is_unverified(self):
        self.data["sections"][2]["source_ids"] = []
        self.save()
        self.assertEqual(self.section()["freshness"]["state"], "unverified")

    def test_included_child_source_change_and_missing_are_not_current(self):
        child_source = self.scope / "child.txt"
        child_source.write_text("Child source", encoding="utf-8")
        self.data["sources"][1] = {"path": "child.txt", "sha256": self.digest(child_source)}
        self.save()
        self.assertEqual(self.section()["freshness"]["state"], "current")
        child_source.write_text("Edited child source", encoding="utf-8")
        self.assertEqual(self.section()["freshness"]["state"], "changed")
        child_source.unlink()
        self.assertEqual(self.section()["freshness"]["state"], "missing")
        self.assertEqual(self.section("child")["freshness"]["state"], "current")

    def test_cli_errors_are_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = reader.main([])
        self.assertEqual(status, 1)
        self.assertIn("--scope-root", json.loads(output.getvalue())["error"])
        self.assertEqual(self.call("--query", "x", "--section", "page.html#topic")[0], 1)
        self.assertEqual(self.call("--max-results", "bad")[0], 1)


if __name__ == "__main__":
    unittest.main()
