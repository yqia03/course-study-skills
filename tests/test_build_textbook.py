"""CLI integration checks for confined textbook builds and evidence catalogs."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


BUILDER = Path(__file__).resolve().parents[1] / "skills/learning-notes/scripts/build_textbook.py"
BODY = '<h2 id="intro" data-aliases="Basics|基础">Introduction</h2><p>Private full paragraph.</p><h3 id="detail">Detail</h3><p>More text.</p>'


class TextbookBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scope = self.root / "lecture5"
        self.scope.mkdir()
        self.body = self.scope / "draft.html"
        self.body.write_text(BODY, encoding="utf-8")

    def run_builder(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(BUILDER), "--scope-root", str(self.scope), *map(str, args)],
                                capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def single(self, *args, ok=True):
        return self.run_builder("--body", self.body, "--title", "Lecture 5", *args, ok=ok)

    def catalog(self, config=None):
        path = self.scope / "evidence.json"
        path.write_text(json.dumps(config or {}), encoding="utf-8")
        return path

    def read_index(self, directory=None):
        return json.loads(((directory or self.scope / "textbook") / "textbook-index.json").read_text(encoding="utf-8"))

    def book(self):
        chapter = self.scope / "second.html"
        chapter.write_text('<h2 id="second">Second chapter</h2><p>Second content.</p>', encoding="utf-8")
        manifest = self.scope / "book.json"
        manifest.write_text(json.dumps({"pages": [
            {"path": "index.html", "title": "Start", "body": "draft.html"},
            {"path": "chapters/two.html", "title": "Next", "body": "second.html"},
        ]}), encoding="utf-8")
        return manifest

    def test_single_default_confined_and_no_metadata_required(self):
        self.single()
        output = self.scope / "textbook/index.html"
        document = output.read_text(encoding="utf-8")
        self.assertIn('content="learning-notes textbook-v2"', document)
        self.assertIn('id="ln-search"', document)
        self.assertIn('id="intro"', document)
        self.assertFalse((output.parent / "textbook-index.json").exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["lecture5"])
        self.single()  # A generated textbook can be rebuilt.

    def test_single_catalog_hashes_sources_maps_sections_and_defaults_partial(self):
        source = self.scope / "slides.bin"
        raw = b"Raw source\r\n\x00\xff"
        source.write_bytes(raw)
        metadata = self.catalog({"sources": [{"path": "slides.bin"}],
                                 "section_sources": {"index.html#intro": ["slides.bin"]}})
        self.single("--catalog", metadata)
        index = self.read_index()
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(index["generated_by"], "learning-notes")
        self.assertEqual(index["entry"], "index.html")
        self.assertEqual(index["scope_root"], "..")
        self.assertEqual(index["coverage"], "partial")
        self.assertEqual(index["limitations"], [])
        self.assertEqual(index["sources"], [{"path": "slides.bin", "sha256": hashlib.sha256(raw).hexdigest()}])
        self.assertEqual(index["sections"][0], {"path": "index.html", "anchor": "intro", "title": "Introduction",
                                                "aliases": ["Basics", "基础"], "source_ids": [0]})
        self.assertEqual(index["sections"][1]["source_ids"], [])
        self.assertNotIn("Private full paragraph", json.dumps(index))
        page = self.scope / "textbook/index.html"
        self.assertEqual(index["pages"], [{"path": "index.html", "sha256": hashlib.sha256(page.read_bytes()).hexdigest()}])
        self.single("--catalog", metadata)  # A generated catalog can be rebuilt.

    def test_multi_page_catalog_and_relative_navigation(self):
        manifest = self.book()
        metadata = self.catalog({"coverage": "complete", "limitations": ["Example remains informal"],
                                 "sources": [{"path": "draft.html"}, {"path": "second.html"}],
                                 "section_sources": {"chapters/two.html#second": ["second.html"]}})
        self.run_builder("--book", manifest, "--catalog", metadata)
        index = self.read_index()
        self.assertEqual(index["coverage"], "complete")
        self.assertEqual(index["limitations"], ["Example remains informal"])
        self.assertEqual(index["sections"][-1]["source_ids"], [1])
        self.assertEqual(index["sections"][-1]["path"], "chapters/two.html")
        chapter = self.scope / "textbook/chapters/two.html"
        self.assertIn('../index.html#page-title', chapter.read_text(encoding="utf-8"))
        self.assertEqual(len(index["pages"]), 2)

    def test_explicit_destination_inside_scope_and_adjacent_index(self):
        output = self.scope / "custom/lesson.html"
        self.single("--output", output, "--catalog", self.catalog())
        index = self.read_index(output.parent)
        self.assertEqual(index["entry"], "lesson.html")
        self.assertEqual(index["scope_root"], "..")
        self.assertEqual(index["sources"], [])
        self.assertTrue(all(section["source_ids"] == [] for section in index["sections"]))

    def test_parent_destinations_and_symlinks_are_rejected(self):
        for destination in (self.root / "index.html", self.scope / "../escaped.html"):
            with self.subTest(destination=destination):
                self.single("--output", destination, ok=False)
                self.assertFalse(destination.exists())
        link = self.scope / "linked"
        link.symlink_to(self.root, target_is_directory=True)
        self.single("--output", link / "escape.html", ok=False)
        self.run_builder("--book", self.book(), "--output-dir", link / "book", ok=False)
        self.assertFalse((self.root / "escape.html").exists())
        self.assertFalse((self.root / "book").exists())

    def test_index_symlink_escape_preflight_leaves_no_html(self):
        delivery = self.scope / "textbook"
        delivery.mkdir()
        outside = self.root / "outside.json"
        outside.write_text("original", encoding="utf-8")
        (delivery / "textbook-index.json").symlink_to(outside)
        self.single("--catalog", self.catalog(), ok=False)
        self.assertFalse((delivery / "index.html").exists())
        self.assertEqual(outside.read_text(), "original")

    def test_unrelated_index_preflight_leaves_no_html(self):
        delivery = self.scope / "textbook"
        delivery.mkdir()
        index = delivery / "textbook-index.json"
        index.write_text('{"user": "data"}', encoding="utf-8")
        self.run_builder("--book", self.book(), "--catalog", self.catalog(), ok=False)
        self.assertFalse((delivery / "index.html").exists())
        self.assertFalse((delivery / "chapters").exists())
        self.assertEqual(index.read_text(), '{"user": "data"}')

    def test_unrelated_html_preflight_leaves_all_files_unchanged(self):
        delivery = self.scope / "textbook"
        (delivery / "chapters").mkdir(parents=True)
        existing = delivery / "chapters/two.html"
        existing.write_text("User writing", encoding="utf-8")
        self.run_builder("--book", self.book(), "--catalog", self.catalog(), ok=False)
        self.assertFalse((delivery / "index.html").exists())
        self.assertFalse((delivery / "textbook-index.json").exists())
        self.assertEqual(existing.read_text(), "User writing")

    def test_body_and_catalog_sources_cannot_be_overwritten_even_if_generated(self):
        self.single("--output", self.body, ok=False)
        self.assertEqual(self.body.read_text(), BODY)
        generated = self.scope / "source.html"
        self.single("--output", generated)
        original = generated.read_bytes()
        metadata = self.catalog({"sources": [{"path": "source.html"}]})
        self.single("--output", generated, "--catalog", metadata, ok=False)
        self.assertEqual(generated.read_bytes(), original)
        self.assertFalse((self.scope / "textbook-index.json").exists())

    def test_source_cannot_overlap_index(self):
        self.single("--catalog", self.catalog())
        index_path = self.scope / "textbook/textbook-index.json"
        original = index_path.read_bytes()
        metadata = self.catalog({"sources": [{"path": "textbook/textbook-index.json"}]})
        self.single("--catalog", metadata, ok=False)
        self.assertEqual(index_path.read_bytes(), original)

    def test_inputs_and_evidence_cannot_escape_scope(self):
        outside = self.root / "outside.html"
        outside.write_text(BODY, encoding="utf-8")
        linked = self.scope / "linked-source.html"
        linked.symlink_to(outside)
        self.run_builder("--body", outside, "--title", "Outside", ok=False)
        self.run_builder("--body", linked, "--title", "Outside", ok=False)
        self.single("--catalog", outside, ok=False)
        for name in ("../outside.html", str(outside), "linked-source.html"):
            with self.subTest(name=name):
                self.single("--catalog", self.catalog({"sources": [{"path": name}]}), ok=False)
        self.single("--catalog", self.catalog({"sources": [{"path": "."}]}), ok=False)
        manifest = self.book()
        config = json.loads(manifest.read_text())
        config["pages"][1]["body"] = "../outside.html"
        manifest.write_text(json.dumps(config), encoding="utf-8")
        self.run_builder("--book", manifest, ok=False)
        self.assertFalse((self.scope / "textbook").exists())

    def test_unknown_mapping_and_bad_metadata_fail_before_writes(self):
        configs = [
            {"section_sources": {"index.html#missing": []}},
            {"section_sources": {"index.html#intro": ["missing.pdf"]}},
            {"coverage": "maybe"}, {"coverage": []}, {"limitations": "none"},
        ]
        for config in configs:
            with self.subTest(config=config):
                self.single("--catalog", self.catalog(config), ok=False)
                self.assertFalse((self.scope / "textbook").exists())

    def test_scope_is_required_and_default_book_requires_index_entry(self):
        result = subprocess.run([sys.executable, str(BUILDER), "--body", str(self.body), "--title", "Lesson"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--scope-root", result.stderr)
        manifest = self.book()
        config = json.loads(manifest.read_text())
        config["pages"][0]["path"] = "start.html"
        manifest.write_text(json.dumps(config), encoding="utf-8")
        self.run_builder("--book", manifest, ok=False)
        self.run_builder("--book", manifest, "--output-dir", self.scope / "explicit")
        self.assertTrue((self.scope / "explicit/start.html").exists())


if __name__ == "__main__":
    unittest.main()
