#!/usr/bin/env python3
"""
gen_index.py

Walks a Go codebase and produces a nested JSON index of folders -> files ->
exported entities (functions, methods, types, consts, vars), including
doc-comment summaries, start/stop line numbers, README-sourced descriptions,
and inter-package dependencies (which exported entities of which internal
packages a file actually uses). Pure Python (stdlib only) -- no Go toolchain
required (git is used only if --branch is passed).

Usage:
    python3 gen_index.py [root_dir] [--git-ref NAME] [--path FOLDER/PATH] [--max-depth N] > index.json

  root_dir     Directory to scan (default: current directory)
  --git-ref    Read the codebase as of this git branch/tag/commit instead of
               the working tree. Uses 'git archive' into a temp dir, so your
               working tree is never touched or checked out.
  --path       Scope the output to one folder's subtree, e.g. "features/ai"
               (like an XPath into the index). The whole codebase is still
               scanned first so dependency resolution stays accurate even
               when the dependency lives outside the selected subtree; only
               the *output* is narrowed to that path.
  --max-depth  Scanning and dependency resolution always cover the whole
               tree (a deeply nested file can still be a dependency target),
               but the *output* JSON tree is cut off beyond this depth.
               Depth 0 is root_dir itself (or the --path node, if given).
               Folders beyond the limit still appear (with their
               description, if any) but get "truncated": true instead of
               expanded contents.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Entity extraction (functions, methods, types, consts, vars)
# ---------------------------------------------------------------------------

FUNC_RE = re.compile(
    r'^\s*func\s+(?:\((?P<recv_name>\w+)\s+(?P<recv_type>\*?\w+)\)\s+)?'
    r'(?P<name>\w+)\s*\('
)
TYPE_BLOCK_RE = re.compile(r'^\s*type\s+(?P<name>\w+)\s+(?P<kind>struct|interface)\b')
TYPE_SINGLE_RE = re.compile(r'^\s*type\s+(?P<name>\w+)\s*(?:=)?\s*\S')
BLOCK_OPEN_RE = re.compile(r'^\s*(?P<keyword>const|var)\s*\(\s*$')
BLOCK_CLOSE_RE = re.compile(r'^\s*\)\s*$')
SINGLE_DECL_RE = re.compile(r'^\s*(?P<keyword>const|var)\s+(?P<rest>.+)$')
IDENT_RE = re.compile(r'^\s*(\w+)')

PACKAGE_RE = re.compile(r'^\s*package\s+(?P<name>\w+)')
IMPORT_BLOCK_OPEN_RE = re.compile(r'^\s*import\s*\(\s*$')
IMPORT_LINE_RE = re.compile(r'^\s*(?:(?P<alias>_|\.|\w+)\s+)?"(?P<path>[^"]+)"')
IMPORT_SINGLE_RE = re.compile(r'^\s*import\s+(?:(?P<alias>_|\.|\w+)\s+)?"(?P<path>[^"]+)"\s*$')
MODULE_RE = re.compile(r'^\s*module\s+(\S+)')

SKIP_DIRS = {".git", "vendor", "node_modules"}


def is_exported(name):
    return bool(name) and name[0].isupper()


def names_from_decl_segment(segment):
    """'Foo, Bar int' -> ['Foo', 'Bar']; 'Foo' -> ['Foo']"""
    names = []
    for part in segment.split(","):
        m = IDENT_RE.match(part)
        if m:
            names.append(m.group(1))
    return names


def find_closing_brace_line(lines, start_idx):
    """Scan forward from start_idx counting braces to find the closing line."""
    depth = 0
    seen_open = False
    for i in range(start_idx, len(lines)):
        code_part = lines[i].split("//", 1)[0]
        for ch in code_part:
            if ch == "{":
                depth += 1
                seen_open = True
            elif ch == "}":
                depth -= 1
                if seen_open and depth == 0:
                    return i
    return start_idx


def extract_doc_comment(lines, line_idx):
    """Collect contiguous '//' comment lines immediately above line_idx."""
    comments = []
    i = line_idx - 1
    while i >= 0 and lines[i].strip().startswith("//"):
        comments.append(lines[i].strip().lstrip("/").strip())
        i -= 1
    comments.reverse()
    return " ".join(comments).strip()


def extract_package_doc(lines):
    for idx, line in enumerate(lines):
        if PACKAGE_RE.match(line):
            return extract_doc_comment(lines, idx)
    return ""


def extract_package_name(lines):
    for line in lines:
        m = PACKAGE_RE.match(line)
        if m:
            return m.group("name")
    return None


def extract_entities(lines):
    """Returns {'summary': str, 'children': [...]} for exported entities."""
    file_summary = extract_package_doc(lines)
    children = []

    def add_entity(name, kind, start_idx, end_idx, receiver=None):
        if not is_exported(name):
            return
        entry = {
            "name": name,
            "kind": kind,
            "start_line": start_idx + 1,
            "stop_line": end_idx + 1,
        }
        if receiver:
            entry["receiver"] = receiver
        summary = extract_doc_comment(lines, start_idx)
        if summary:
            entry["summary"] = summary
        children.append(entry)

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        fm = FUNC_RE.match(line)
        if fm:
            end_idx = find_closing_brace_line(lines, i)
            kind = "method" if fm.group("recv_type") else "function"
            add_entity(fm.group("name"), kind, i, end_idx, receiver=fm.group("recv_type"))
            i = end_idx + 1
            continue

        tb = TYPE_BLOCK_RE.match(line)
        if tb:
            end_idx = find_closing_brace_line(lines, i)
            add_entity(tb.group("name"), "type", i, end_idx)
            i = end_idx + 1
            continue

        ts = TYPE_SINGLE_RE.match(line)
        if ts:
            add_entity(ts.group("name"), "type", i, i)
            i += 1
            continue

        bo = BLOCK_OPEN_RE.match(line)
        if bo:
            keyword = bo.group("keyword")
            j = i + 1
            while j < n and not BLOCK_CLOSE_RE.match(lines[j]):
                inner = lines[j].strip()
                if inner and not inner.startswith("//"):
                    left = inner.split("=", 1)[0]
                    for nm in names_from_decl_segment(left):
                        add_entity(nm, keyword, j, j)
                j += 1
            i = j + 1
            continue

        sd = SINGLE_DECL_RE.match(line)
        if sd:
            keyword = sd.group("keyword")
            left = sd.group("rest").split("=", 1)[0]
            for nm in names_from_decl_segment(left):
                add_entity(nm, keyword, i, i)
            i += 1
            continue

        i += 1

    result = {"children": children}
    if file_summary:
        result["summary"] = file_summary
    return result


def extract_imports(lines):
    """Returns [{'path': str, 'alias': str|None}, ...]. alias is '_' or '.'
    for blank/dot imports, a plain identifier for an explicit alias, or None
    when the file uses the package's own declared name."""
    imports = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if IMPORT_BLOCK_OPEN_RE.match(line):
            j = i + 1
            while j < n and not BLOCK_CLOSE_RE.match(lines[j]):
                inner = lines[j].strip()
                if inner and not inner.startswith("//"):
                    m = IMPORT_LINE_RE.match(inner)
                    if m:
                        imports.append({"path": m.group("path"), "alias": m.group("alias")})
                j += 1
            i = j + 1
            continue
        m2 = IMPORT_SINGLE_RE.match(line)
        if m2:
            imports.append({"path": m2.group("path"), "alias": m2.group("alias")})
        i += 1
    return imports


def find_module_path(root_dir):
    go_mod = os.path.join(root_dir, "go.mod")
    if not os.path.isfile(go_mod):
        return None
    with open(go_mod, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = MODULE_RE.match(line)
            if m:
                return m.group(1)
    return None


# ---------------------------------------------------------------------------
# README.md parsing (folder description + "| File | Purpose |" table)
# ---------------------------------------------------------------------------

README_ROW_RE = re.compile(r'^\|(.+)\|(.+)\|\s*$')
README_LINK_RE = re.compile(r'\[`?([^`\]]+)`?\]\(([^)]+)\)')
README_SEPARATOR_RE = re.compile(r'^\|[\s:-]+\|[\s:-]+\|\s*$')


def parse_readme(readme_path):
    """Returns (description, [{'filename':..., 'description':...}, ...])."""
    with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    desc_lines = []
    files = []
    in_table = False
    past_header = False

    for line in lines:
        stripped = line.strip()

        if not past_header:
            if stripped.startswith("#"):
                past_header = True
            continue

        if stripped.startswith("|"):
            if README_SEPARATOR_RE.match(stripped):
                in_table = True
                continue
            m = README_ROW_RE.match(stripped)
            if m and in_table:
                col1, col2 = m.group(1).strip(), m.group(2).strip()
                link_m = README_LINK_RE.search(col1)
                filename = link_m.group(2) if link_m else col1.strip("`").strip()
                files.append({"filename": filename, "description": col2})
            continue

        if not in_table and stripped:
            desc_lines.append(stripped)

    return " ".join(desc_lines).strip(), files


def checkout_branch_to_tempdir(repo_dir, branch):
    """Extracts the given branch/ref's tree into a fresh temp directory using
    'git archive', without touching the caller's working tree or index.
    Returns the temp directory path; caller is responsible for cleanup."""
    tmpdir = tempfile.mkdtemp(prefix="gen_index_")
    try:
        archive = subprocess.run(
            ["git", "-C", repo_dir, "archive", branch],
            capture_output=True,
        )
        if archive.returncode != 0:
            raise RuntimeError(archive.stderr.decode(errors="replace").strip())

        tar_proc = subprocess.run(
            ["tar", "-x", "-C", tmpdir],
            input=archive.stdout,
            capture_output=True,
        )
        if tar_proc.returncode != 0:
            raise RuntimeError(tar_proc.stderr.decode(errors="replace").strip())
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    return tmpdir


def new_folder(path):
    return {"path": path, "files": {}, "folders": {}}


def _get_folder(root, rel_dir):
    """Fetch or create the folder node at rel_dir (e.g. 'features/ai')."""
    if rel_dir == ".":
        return root
    folder = root
    for part in rel_dir.split(os.sep):
        folder = folder["folders"].setdefault(part, new_folder(part))
    return folder


# ---------------------------------------------------------------------------
# Two-pass index build:
#   Pass 1 -- read every file once; record its entities, imports, package
#             name, and raw text; aggregate each package's exported entities.
#   Pass 2 -- for each file, resolve its internal imports against the
#             package-export map and grep the file's own text for actual
#             "alias.Entity" usages, producing a 'depends_on' field.
# ---------------------------------------------------------------------------

def build_index(root_dir):
    module = find_module_path(root_dir)
    if module is None:
        sys.stderr.write("note: no go.mod found; falling back to path-suffix matching for internal imports\n")

    file_records = []          # list of dicts, one per .go file
    package_exports = {}       # rel_dir -> {entity_name: kind}
    package_names = {}         # rel_dir -> declared "package X" name
    all_rel_dirs = []          # every directory visited, in walk order
    folder_readme = {}         # rel_dir -> (description, [{'filename','description'}, ...])

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root_dir)
        all_rel_dirs.append(rel_dir)

        readme_path = os.path.join(dirpath, "README.md")
        if os.path.isfile(readme_path):
            try:
                folder_readme[rel_dir] = parse_readme(readme_path)
            except OSError as e:
                sys.stderr.write(f"skipping {readme_path}: {e}\n")

        go_files = [f for f in filenames if f.endswith(".go")]

        for fname in sorted(go_files):
            full_path = os.path.join(dirpath, fname)
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError as e:
                sys.stderr.write(f"skipping {full_path}: {e}\n")
                continue
            lines = text.splitlines()

            entities = extract_entities(lines)
            imports = extract_imports(lines)
            pkg_name = extract_package_name(lines)

            file_records.append({
                "rel_dir": rel_dir,
                "fname": fname,
                "text": text,
                "entities": entities,
                "imports": imports,
            })

            if pkg_name and rel_dir not in package_names:
                package_names[rel_dir] = pkg_name

            exports = package_exports.setdefault(rel_dir, {})
            for ent in entities["children"]:
                exports[ent["name"]] = ent["kind"]

    def import_path_for(rel_dir):
        if module is None:
            return None
        posix_rel = rel_dir.replace(os.sep, "/")
        return module if posix_rel == "." else f"{module}/{posix_rel}"

    # import_path -> rel_dir, used to resolve internal imports back to a
    # local package we actually scanned.
    import_path_to_reldir = {}
    for rel_dir in package_exports:
        ip = import_path_for(rel_dir)
        if ip:
            import_path_to_reldir[ip] = rel_dir

    def resolve_internal(import_path):
        if import_path in import_path_to_reldir:
            return import_path_to_reldir[import_path]
        if module is None:
            # Fallback with no go.mod: match by folder-path suffix.
            posix_path = import_path.rstrip("/")
            best = None
            for rel_dir in package_exports:
                posix_rel = rel_dir.replace(os.sep, "/")
                suffix = posix_rel if posix_rel != "." else ""
                if suffix and (posix_path == suffix or posix_path.endswith("/" + suffix)):
                    if best is None or len(suffix) > len(best[1]):
                        best = (rel_dir, suffix)
            return best[0] if best else None
        return None

    root = new_folder(".")

    for rec in file_records:
        depends_on = []
        for imp in rec["imports"]:
            path = imp["path"]
            alias = imp["alias"]

            target_rel_dir = resolve_internal(path)
            if target_rel_dir is None or target_rel_dir == rec["rel_dir"]:
                continue  # external dependency, or a (rare) self-import

            entry = {"package": path}

            if alias == "_":
                entry["entities"] = []
                entry["note"] = "blank import (side effects only, no entities referenced)"
            elif alias == ".":
                entry["entities"] = []
                entry["note"] = "dot import; identifiers are unqualified so usage can't be reliably matched"
            else:
                local_name = alias or package_names.get(
                    target_rel_dir,
                    target_rel_dir.replace(os.sep, "/").rsplit("/", 1)[-1] if target_rel_dir != "." else module,
                )
                exports = package_exports.get(target_rel_dir, {})
                used = []
                for ent_name in sorted(exports):
                    pattern = re.compile(r'\b' + re.escape(local_name) + r'\.' + re.escape(ent_name) + r'\b')
                    if pattern.search(rec["text"]):
                        used.append(ent_name)
                entry["entities"] = used

            depends_on.append(entry)

        node = dict(rec["entities"])  # {'children': [...], 'summary': ... (optional)}
        if depends_on:
            node["depends_on"] = depends_on

        folder = _get_folder(root, rec["rel_dir"])
        folder["files"][rec["fname"]] = node

    # --- merge in README.md folder descriptions and file-table entries ---
    for rel_dir in all_rel_dirs:
        folder = _get_folder(root, rel_dir)
        if rel_dir not in folder_readme:
            continue
        description, readme_files = folder_readme[rel_dir]
        if description:
            folder["description"] = description

        dirpath = root_dir if rel_dir == "." else os.path.join(root_dir, rel_dir)
        for entry in readme_files:
            fname = entry["filename"]
            existing = folder["files"].get(fname)
            if existing is not None:
                # Already present from the .go scan -- just attach the
                # human-written description alongside the code-derived one.
                existing["description"] = entry["description"]
            else:
                # Non-.go file (yaml, json, txt, ...) or a .go file that
                # wasn't scanned for some reason -- verify it actually exists.
                file_node = {"description": entry["description"]}
                if not os.path.isfile(os.path.join(dirpath, fname)):
                    file_node["missing"] = True
                folder["files"][fname] = file_node

    return {"root": root}


def truncate_depth(folder, depth, max_depth):
    """Returns a copy of `folder` with contents beyond max_depth collapsed
    into a 'truncated': true marker. Scanning/dependency resolution already
    ran over the full tree before this is applied -- this only shapes the
    output."""
    if max_depth is not None and depth >= max_depth:
        has_content = bool(folder["files"]) or bool(folder["folders"])
        node = {"path": folder["path"]}
        if "description" in folder:
            node["description"] = folder["description"]
        if has_content:
            node["truncated"] = True
        return node

    node = dict(folder)
    node["folders"] = {
        name: truncate_depth(sub, depth + 1, max_depth)
        for name, sub in folder["folders"].items()
    }
    return node


def get_subtree(root, path):
    """Navigate root down to the folder at `path` (e.g. 'features/ai'),
    XPath-style. Returns that folder's node, or None if any segment along
    the path doesn't exist."""
    path = path.strip("/").strip("\\")
    if not path or path == ".":
        return root
    node = root
    for part in re.split(r'[/\\]', path):
        if not part:
            continue
        node = node["folders"].get(part)
        if node is None:
            return None
    return node


def main():
    parser = argparse.ArgumentParser(description="Build a JSON index of a Go codebase.")
    parser.add_argument("root_dir", nargs="?", default=".", help="Directory to scan")
    parser.add_argument("--git-ref", help="Scan this git branch/tag/commit instead of the working tree")
    parser.add_argument("--path", help="Scope output to one folder's subtree, e.g. 'features/ai'")
    parser.add_argument("--max-depth", type=int, default=None,
                         help="Only expand folders down to this depth in the output "
                              "(depth 0 = root_dir, or the --path node if given)")
    args = parser.parse_args()

    scan_dir = args.root_dir
    tmpdir = None

    if args.git_ref:
        try:
            tmpdir = checkout_branch_to_tempdir(args.root_dir, args.git_ref)
        except Exception as e:
            sys.stderr.write(f"error: could not read git ref '{args.git_ref}': {e}\n")
            sys.exit(1)
        scan_dir = tmpdir

    try:
        index = build_index(scan_dir)
        root = index["root"]

        if args.path:
            root = get_subtree(root, args.path)
            if root is None:
                sys.stderr.write(f"error: path '{args.path}' not found in the scanned tree\n")
                sys.exit(1)

        if args.max_depth is not None:
            root = truncate_depth(root, 0, args.max_depth)

        json.dump({"root": root}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()