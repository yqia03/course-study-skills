#!/usr/bin/env python3
"""Inventory a user-selected material directory without reading file contents."""

import argparse
import json
import os
from pathlib import Path
import sys


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".cache",
    ".codex", ".agents", ".aws",
}
SKIP_FILES = {".DS_Store", "Thumbs.db"}
FORMATS = {
    "document": {".pdf", ".doc", ".docx", ".odt", ".rtf", ".epub"},
    "slides": {".ppt", ".pptx", ".odp", ".key"},
    "text": {".txt", ".md", ".rst", ".tex", ".html", ".htm", ".srt", ".vtt"},
    "data": {".csv", ".tsv", ".xlsx", ".xls", ".ods", ".json", ".xml", ".yaml", ".yml"},
    "code": {".py", ".r", ".m", ".js", ".ts", ".sql", ".ipynb", ".java", ".c", ".cpp"},
    "image": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".tif", ".tiff", ".heic"},
    "media": {".mp3", ".wav", ".m4a", ".mp4", ".mov", ".webm", ".ogg", ".flac"},
    "archive": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz"},
}
GENERATED_BY = "learning-notes/inventory_materials.py"


def inventory(root, excludes=(), output=None, overwrite=False):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("The material root must be a directory.")
    excluded = set()
    for value in excludes:
        candidate = (root / value).resolve()
        if candidate == root or not candidate.is_relative_to(root):
            raise ValueError("Exclusions must be paths inside the material root.")
        excluded.add(candidate)
    output_path = Path(output).resolve() if output else None
    if output_path is not None:
        if output_path == root or not output_path.is_relative_to(root):
            raise ValueError("Output must be a file inside the material root.")
        if output_path.exists():
            if not overwrite:
                raise ValueError("Output already exists; choose a new path or pass --overwrite for your manifest.")
            if not output_path.is_file():
                raise ValueError("Output must be a file, not a directory or special path.")
            try:
                previous = json.loads(output_path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                previous = None
            if not isinstance(previous, dict) or previous.get("generated_by") != GENERATED_BY:
                raise ValueError("Refusing to overwrite an original file; only generated inventory manifests may be replaced.")
    records = []

    def record(path, kind, status, **extra):
        records.append({"path": path.relative_to(root).as_posix(), "kind": kind,
                        "status": status, **extra})

    def walk(directory):
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name.casefold())
        except OSError as error:
            record(directory, "directory", "unreadable", reason=str(error))
            return
        for entry in entries:
            path = Path(entry.path)
            try:
                if entry.is_symlink():
                    record(path, "symlink", "needs_review", target=os.readlink(path),
                           reason="Not followed; verify target scope and avoid duplicates.")
                elif path in excluded or path == output_path:
                    record(path, "directory" if entry.is_dir() else "file", "excluded",
                           reason="Explicit exclusion or inventory output.")
                elif entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_DIRS:
                        record(path, "directory", "excluded", reason="Tooling, dependency, or cache directory.")
                    else:
                        walk(path)
                elif entry.is_file(follow_symlinks=False):
                    if entry.name in SKIP_FILES:
                        record(path, "file", "excluded", reason="Operating-system metadata.")
                    else:
                        suffix = path.suffix.lower()
                        hint = next((name for name, extensions in FORMATS.items()
                                     if suffix in extensions), "unknown")
                        record(path, "file", "needs_review", format_hint=hint,
                               size_bytes=entry.stat(follow_symlinks=False).st_size)
                else:
                    record(path, "special", "excluded", reason="Not a regular file or directory.")
            except OSError as error:
                record(path, "unknown", "unreadable", reason=str(error))

    walk(root)
    return {
        "generated_by": GENERATED_BY,
        "root": str(root),
        "inventory_only": True,
        "unreadable_paths": sum(item["status"] == "unreadable" for item in records),
        "candidate_files": sum(item["kind"] == "file" and item["status"] == "needs_review"
                               for item in records),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, help="JSON manifest; defaults to stdout.")
    parser.add_argument("--exclude", action="append", default=[], help="A path relative to root; repeatable.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing generated inventory manifest.")
    args = parser.parse_args()
    try:
        result = inventory(args.root, args.exclude, args.output, args.overwrite)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Inventoried {result['candidate_files']} candidate files: {args.output}")
    else:
        print(payload, end="")
    if result["unreadable_paths"]:
        print("Some paths could not be inspected; see the manifest.", file=sys.stderr)


if __name__ == "__main__":
    main()
