#!/usr/bin/env python3
"""Build an offline textbook, or all pages of one book with a shared search index."""

import argparse
import html
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
from string import Template
from urllib.parse import quote


ASSETS = Path(__file__).resolve().parents[1] / "assets"


class ChapterIndex(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.headings = []
        self.current = None
        self.section = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            if identifier in self.ids or identifier in {"main", "page-title"} or identifier.startswith("ln-"):
                raise ValueError(f"Duplicate or reserved id: {identifier}")
            self.ids.add(identifier)
        if tag in {"html", "head", "body", "h1", "style", "script", "base"}:
            raise ValueError(f"Supply an authored body fragment without <{tag}>.")
        if tag in {"h2", "h3"}:
            if self.current:
                raise ValueError("Headings cannot be nested.")
            if not identifier or any(character.isspace() for character in identifier):
                raise ValueError(f"<{tag}> needs a unique id without whitespace.")
            self.current = {"level": tag, "id": identifier, "title_parts": [], "parts": [],
                            "aliases": [part.strip() for part in attributes.get("data-aliases", "").split("|") if part.strip()]}
            self.section = self.current
        elif self.section and tag in {"p", "li", "div", "summary", "br", "td", "th"}:
            self.section["parts"].append(" ")

    def handle_data(self, data):
        if self.current:
            self.current["title_parts"].append(data)
        elif self.section:
            self.section["parts"].append(data)

    def handle_endtag(self, tag):
        if self.current and tag == self.current["level"]:
            title = " ".join("".join(self.current.pop("title_parts")).split())
            if not title:
                raise ValueError("A heading must have readable text.")
            self.current["title"] = title
            self.headings.append(self.current)
            self.current = None
        if self.section and tag in {"p", "li", "div", "summary", "td", "th"}:
            self.section["parts"].append(" ")


def parse_body(body):
    index = ChapterIndex()
    index.feed(body)
    index.close()
    if index.current or not any(item["level"] == "h2" for item in index.headings):
        raise ValueError("The fragment needs at least one complete h2 chapter heading.")
    for item in index.headings:
        item["text"] = " ".join("".join(item.pop("parts")).split())
    return index.headings


def local_href(current, target, anchor=""):
    path = "" if current == target and anchor else quote(posixpath.relpath(target, posixpath.dirname(current) or "."), safe="/")
    return path + ("#" + quote(anchor, safe="") if anchor else "")


def toc_item(href, title, level="h2"):
    return f'<li class="toc-{level}"><a href="{html.escape(href, quote=True)}">{html.escape(title)}</a></li>'


def json_for_html(value):
    # A source title containing </script> must remain data, never close the container.
    return json.dumps(value, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def render_pages(pages, course, assets=None):
    assets = assets or ASSETS
    parsed = [(page, parse_body(page["body"])) for page in pages]
    template = Template((assets / "textbook.html").read_text(encoding="utf-8"))
    css = (assets / "textbook.css").read_text(encoding="utf-8")
    javascript = (assets / "textbook.js").read_text(encoding="utf-8")
    rendered = {}
    for position, (page, headings) in enumerate(parsed):
        current = page["path"]
        toc = "\n".join(toc_item("#" + quote(item["id"], safe=""), item["title"], item["level"]) for item in headings)
        if len(pages) == 1:
            course_toc = "\n".join(toc_item("#" + quote(item["id"], safe=""), item["title"]) for item in headings if item["level"] == "h2")
        else:
            course_toc = "\n".join(toc_item(local_href(current, other["path"], "page-title"), other["title"]) for other in pages)
        entries = []
        for other, other_headings in parsed:
            chapter = other["title"]
            for item in other_headings:
                if item["level"] == "h2":
                    chapter = item["title"]
                entries.append({"title": item["title"], "aliases": item["aliases"], "text": item["text"],
                                "chapter": other["title"] + " · " + chapter,
                                "href": local_href(current, other["path"], item["id"])})
        neighbors = []
        for offset, label in [(-1, "上一章"), (1, "下一章")]:
            neighbor = position + offset
            if 0 <= neighbor < len(pages):
                other = pages[neighbor]
                href = html.escape(local_href(current, other["path"], "page-title"), quote=True)
                neighbors.append(f'<a href="{href}">{label}：{html.escape(other["title"])}</a>')
        page_links = '<nav class="page-links" aria-label="前后章节">' + "".join(neighbors) + '</nav>' if neighbors else ""
        rendered[current] = template.substitute(
            title=html.escape(page["title"]), subtitle=html.escape(page.get("subtitle", "")),
            course=html.escape(course), body=page["body"], toc=toc, course_toc=course_toc,
            home_href=html.escape(local_href(current, pages[0]["path"], "page-title"), quote=True),
            page_links=page_links, css=css, javascript=javascript, book_data=json_for_html({"entries": entries}),
        )
    return rendered


def build_document(body, title, subtitle="", course="自主学习教材", assets=None):
    return render_pages([{"path": "textbook.html", "title": title, "subtitle": subtitle, "body": body}], course, assets)["textbook.html"]


def load_book(manifest, scope=None):
    config = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("pages"), list) or not config["pages"]:
        raise ValueError("Book manifest needs a nonempty pages list.")
    pages, sources, seen = [], {manifest.resolve()}, set()
    for item in config["pages"]:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in ("path", "title", "body")):
            raise ValueError("Each page needs string path, title, and body fields.")
        path = PurePosixPath(item["path"])
        if path.is_absolute() or ".." in path.parts or any(character in item["path"] for character in "\\?#:") or path.suffix.lower() != ".html":
            raise ValueError("Each output path must be a relative .html path inside the delivery directory.")
        output_name = path.as_posix()
        if output_name.casefold() in seen:
            raise ValueError(f"Duplicate output path: {output_name}")
        seen.add(output_name.casefold())
        source = (manifest.parent / item["body"]).resolve(strict=True)
        if scope is not None:
            source = scoped_path(source, scope)
        sources.add(source)
        subtitle = item.get("subtitle", "")
        if not isinstance(subtitle, str):
            raise ValueError("Page subtitle must be a string.")
        pages.append({"path": output_name, "title": item["title"], "subtitle": subtitle, "body": source.read_text(encoding="utf-8")})
    course = config.get("course", "自主学习教材")
    if not isinstance(course, str):
        raise ValueError("Book course must be a string.")
    return pages, course, sources


def scoped_path(path, scope):
    """Resolve existing symlinks, including those in not-yet-created parents."""
    resolved = path.resolve()
    if not resolved.is_relative_to(scope):
        raise ValueError(f"Path escapes --scope-root: {path}")
    return resolved


def relative_path(path, root):
    return Path(os.path.relpath(path, root)).as_posix()


def load_catalog(path, scope):
    """Snapshot evidence bytes once; metadata describes provenance, not correctness."""
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Catalog input must be a JSON object.")
    coverage = config.get("coverage", "partial")
    limitations = config.get("limitations", [])
    sources = config.get("sources", [])
    mapping = config.get("section_sources", {})
    if not isinstance(coverage, str) or coverage not in {"complete", "partial"}:
        raise ValueError("Catalog coverage must be complete or partial.")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        raise ValueError("Catalog limitations must be a list of strings.")
    if not isinstance(sources, list) or not isinstance(mapping, dict):
        raise ValueError("Catalog needs a sources list and a section_sources object.")
    evidence, identifiers, protected = [], {}, set()
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("Each catalog source needs a string path relative to scope.")
        name = item["path"]
        relative = PurePosixPath(name)
        if not name or relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError(f"Source path must be relative to scope: {name}")
        source = scoped_path(scope / name, scope)
        if not source.is_file():
            raise ValueError(f"Catalog source must be a regular file: {name}")
        canonical = relative_path(source, scope)
        if source in protected:
            raise ValueError(f"Duplicate catalog source: {name}")
        identifiers[name] = len(evidence)
        identifiers[canonical] = len(evidence)
        evidence.append({"path": canonical, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
        protected.add(source)
    for key, names in mapping.items():
        if not isinstance(key, str) or not isinstance(names, list) or not all(isinstance(name, str) and name in identifiers for name in names):
            raise ValueError("section_sources must map page.html#anchor to known source paths.")
    return {"coverage": coverage, "limitations": limitations, "sources": evidence}, mapping, identifiers, protected


def make_catalog(pages, rendered, output_dir, entry, scope, metadata, mapping, identifiers):
    sections, known_keys = [], set()
    for page in pages:
        for heading in parse_body(page["body"]):
            key = page["path"] + "#" + heading["id"]
            known_keys.add(key)
            sections.append({"path": page["path"], "anchor": heading["id"], "title": heading["title"],
                             "aliases": heading["aliases"],
                             "source_ids": list(dict.fromkeys(identifiers[name] for name in mapping.get(key, [])))})
    unknown = mapping.keys() - known_keys
    if unknown:
        raise ValueError(f"Unknown section_sources location: {sorted(unknown)[0]}")
    return {"schema_version": 1, "generated_by": "learning-notes", "entry": relative_path(entry, output_dir),
            "scope_root": relative_path(scope, output_dir), **metadata,
            "pages": [{"path": path, "sha256": hashlib.sha256(document.encode("utf-8")).hexdigest()}
                      for path, document in rendered.items()], "sections": sections}


def generated_catalog(target):
    try:
        existing = json.loads(target.read_text(encoding="utf-8"))
        return isinstance(existing, dict) and existing.get("schema_version") == 1 and existing.get("generated_by") == "learning-notes"
    except (ValueError, OSError):
        return False


def write_outputs(rendered, output_dir, protected, scope_root, catalog=None):
    """Preflight the entire delivery, then write only within the authorized scope."""
    scope = scope_root.resolve(strict=True)
    root = scoped_path(output_dir, scope)
    destinations = [(root / relative, document, False) for relative, document in rendered.items()]
    if catalog is not None:
        destinations.append((root / "textbook-index.json", json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", True))
    checked, seen = [], set()
    for target, document, is_catalog in destinations:
        resolved = scoped_path(target, scope)
        if not resolved.is_relative_to(root) or resolved in seen or resolved.is_relative_to(ASSETS.resolve()):
            raise ValueError(f"Unsafe output destination: {target}")
        if any(resolved == source or (resolved.exists() and source.exists() and resolved.samefile(source)) for source in protected):
            raise ValueError(f"Output would overwrite a source: {target}")
        if resolved.exists():
            generated = resolved.is_file() and (generated_catalog(resolved) if is_catalog else 'content="learning-notes textbook-' in resolved.read_text(encoding="utf-8"))
            if not generated:
                raise ValueError(f"Existing file is not a generated {'catalog' if is_catalog else 'textbook'}; choose a new filename: {target}")
        for parent in resolved.parents:
            if parent.exists() and not parent.is_dir():
                raise ValueError(f"Output parent is not a directory: {parent}")
        seen.add(resolved)
        checked.append((resolved, document))
    if any(left != right and left in right.parents for left in seen for right in seen):
        raise ValueError("Output paths conflict with one another.")
    for target, document in checked:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document, encoding="utf-8")
        print(f"Built textbook: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        "All inputs and destinations must resolve inside --scope-root. Defaults: scope/textbook/index.html "
        "or scope/textbook/ for books (first manifest page must be index.html). "
        "--catalog is optional: its JSON accepts coverage (complete|partial; default partial), "
        "limitations (strings), sources ([{path: relative-to-scope}]), and section_sources "
        "({page.html#anchor: [source paths]}). It emits textbook-index.json with SHA-256 evidence "
        "and heading locations; absent mappings are unverified ([]). Metadata does not certify correctness."))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--body", type=Path, help="Authored HTML fragment for a single file.")
    mode.add_argument("--book", type=Path, help="JSON manifest of all pages in this textbook.")
    parser.add_argument("--scope-root", type=Path, required=True, help="Existing authorized source/output scope; no input or output may escape it.")
    parser.add_argument("--catalog", type=Path, help="Optional JSON evidence metadata; emits a compact textbook-index.json beside the entry / in output-dir.")
    parser.add_argument("--title")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--course", default="自主学习教材")
    parser.add_argument("--output", type=Path, help="Single HTML destination inside scope (default: scope/textbook/index.html).")
    parser.add_argument("--output-dir", type=Path, help="Book destination inside scope (default: scope/textbook).")
    args = parser.parse_args()
    try:
        scope = args.scope_root.resolve(strict=True)
        if not scope.is_dir():
            raise ValueError("--scope-root must be a directory.")
        for name in ("body", "book", "catalog"):
            path = getattr(args, name)
            if path is not None:
                setattr(args, name, scoped_path(path, scope))
        metadata = None
        if args.catalog:
            metadata, mapping, identifiers, evidence = load_catalog(args.catalog, scope)
        if args.book:
            if args.output or args.title:
                parser.error("--book cannot use --output or --title; metadata comes from the manifest.")
            output_dir = scoped_path(args.output_dir or scope / "textbook", scope)
            pages, course, sources = load_book(args.book, scope)
            if not args.output_dir and pages[0]["path"] != "index.html":
                raise ValueError("The default book destination requires index.html as the first manifest page.")
        else:
            if not args.title or args.output_dir:
                parser.error("--body requires --title and cannot use --output-dir.")
            output = scoped_path(args.output or scope / "textbook" / "index.html", scope)
            output_dir = output.parent
            pages = [{"path": output.name, "title": args.title, "subtitle": args.subtitle,
                      "body": args.body.read_text(encoding="utf-8")}]
            course, sources = args.course, {args.body.resolve()}
        rendered = render_pages(pages, course)
        catalog = None
        if metadata is not None:
            sources |= evidence | {args.catalog.resolve()}
            catalog = make_catalog(pages, rendered, output_dir, output_dir / pages[0]["path"], scope, metadata, mapping, identifiers)
        write_outputs(rendered, output_dir, sources, scope, catalog)
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
