# /// script
# requires-python = "==3.13"
# dependencies = ["tomlkit"]
# ///
"""Generate API documentation stubs and update nav in zensical.toml."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.items import AoT, Array, InlineTable, Table

DEFAULT_OPTIONS: dict[str, Any] = {
    "summary": {
        "attributes": True,
        "functions": True,
        "classes": True,
        "type_aliases": True,
        "modules": False,
    },
}


def _format_options(options: dict[str, Any], indent: int = 4) -> str:
    """Format a dict as a YAML-like options block for mkdocstrings."""
    lines: list[str] = []
    prefix = " " * indent
    for key, value in options.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_format_options(value, indent + 4))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, str):
                    lines.append(f'{prefix}    - "{item}"')
                else:
                    lines.append(f"{prefix}    - {item}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


def _make_stub(namespace: str, options: dict[str, Any]) -> str:
    """Build the markdown stub content for a given namespace."""
    stub = f"::: {namespace}"
    if options:
        stub += f"\n    options:\n{_format_options(options, indent=8)}"
    return stub + "\n"


def _init_exports(init_file: Path) -> bool:
    """Return True if an __init__.py exports any public names."""
    text = init_file.read_text().strip()
    if not text:
        return False
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return True
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        return True
    return False


def generate_docs(
    package_root: Path,
    docs_dir: Path,
    namespace: str,
    skip: set[str],
    options: dict[str, Any],
    filters: list[str] | None = None,
) -> bool:
    """Recursively generate API doc stubs for a Python package.

    Returns True if any content was generated.
    """
    has_content = False

    # Check for public .py modules (not __init__.py, not _private)
    for item in sorted(package_root.iterdir()):
        if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
            has_content = True
            break

    # Check for public subpackages (recurse first, create dirs only if needed)
    for item in sorted(package_root.iterdir()):
        name = item.name
        if not item.is_dir() or name.startswith(("_", ".")):
            continue
        if not (item / "__init__.py").exists():
            continue
        child_ns = f"{namespace}.{name}"
        if child_ns in skip:
            continue
        if generate_docs(item, docs_dir / name, child_ns, skip, options, filters):
            has_content = True

    # If no public children, check if __init__.py itself exports anything
    if not has_content:
        has_content = _init_exports(package_root / "__init__.py")

    if not has_content:
        return False

    # Now create the directory and write stubs
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Apply filters to index.md (package-level stubs) to hide dedicated objects
    index_options = options
    if filters:
        index_options = {**options, "filters": filters}
    (docs_dir / "index.md").write_text(_make_stub(namespace, index_options))

    for item in sorted(package_root.iterdir()):
        name = item.name
        if item.is_file() and item.suffix == ".py" and not name.startswith("_"):
            mod_name = item.stem
            if f"{namespace}.{mod_name}" not in skip:
                (docs_dir / f"{mod_name}.md").write_text(
                    _make_stub(f"{namespace}.{mod_name}", options)
                )

    return True


# ---- Nav tree building ----


def _rel(path: Path, docs_dir: Path) -> str:
    """Return path relative to docs_dir, using forward slashes."""
    return path.relative_to(docs_dir).as_posix()


def _build_dir_nav(dir_path: Path, docs_dir: Path) -> dict | str | None:
    """Build a nav entry for a directory."""
    sub_items: list[str | dict] = []

    if (dir_path / "index.md").exists():
        sub_items.append(_rel(dir_path / "index.md", docs_dir))

    for child in sorted(dir_path.iterdir()):
        if child.name == "index.md":
            continue
        if child.is_dir():
            entry = _build_dir_nav(child, docs_dir)
            if entry is not None:
                sub_items.append(entry)
        elif child.suffix == ".md":
            sub_items.append({child.stem: _rel(child, docs_dir)})

    if not sub_items:
        return None
    if len(sub_items) == 1 and isinstance(sub_items[0], str):
        return {dir_path.name: sub_items[0]}
    return {dir_path.name: sub_items}


def _build_api_nav(api_dir: Path, docs_dir: Path) -> list[str | dict]:
    """Build the nav items for the API section."""
    items: list[str | dict] = []

    if (api_dir / "index.md").exists():
        items.append(_rel(api_dir / "index.md", docs_dir))

    for child in sorted(api_dir.iterdir()):
        if child.name == "index.md":
            continue
        if child.is_dir():
            entry = _build_dir_nav(child, docs_dir)
            if entry is not None:
                items.append(entry)

    return items


# ---- TOML nav update ----


def _quote_key(key: str) -> str:
    """Quote a TOML key if it's not a simple identifier."""
    if key.isidentifier() and key.isascii():
        return key
    return f'"{key}"'


def _format_nav_value(value: Any, indent: int) -> str:
    """Format a nav value as properly indented TOML."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, dict):
        key, val = next(iter(value.items()))
        return f"{{ {_quote_key(key)} = {_format_nav_value(val, indent)} }}"
    if isinstance(value, list):
        inner = indent + 2
        lines = ["["]
        for item in value:
            lines.append(f"{' ' * inner}{_format_nav_value(item, inner)},")
        lines.append(f"{' ' * indent}]")
        return "\n".join(lines)
    return str(value)


def _nav_to_python(obj: Any) -> Any:
    """Convert tomlkit objects to plain Python."""
    if isinstance(obj, (InlineTable, Table)):
        return {k: _nav_to_python(v) for k, v in obj.items()}
    if isinstance(obj, (Array, AoT, list)):
        return [_nav_to_python(item) for item in obj]
    return obj


def _find_bracket_end(text: str, start: int) -> int:
    """Find the position of the matching close bracket."""
    depth = 0
    in_string = False
    i = start
    while i < len(text):
        c = text[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise RuntimeError("Unmatched bracket in nav array")


def update_nav(
    toml_path: Path,
    api_dir: Path,
    docs_dir: Path,
    section: str,
    parent: str | None = None,
) -> None:
    """Update a named nav section in zensical.toml."""
    import re

    raw = toml_path.read_text()
    doc = tomlkit.parse(raw)
    nav = doc["project"]["nav"]
    py_nav = _nav_to_python(nav)

    # Find target array
    if parent:
        target = None
        for item in py_nav:
            if isinstance(item, dict) and parent in item:
                target = item[parent]
                break
        if target is None:
            raise RuntimeError(f"Could not find {parent!r} section in nav")
    else:
        target = py_nav

    # Build new section content
    api_items = _build_api_nav(api_dir, docs_dir)

    # Insert or replace section
    found = False
    for item in target:
        if isinstance(item, dict) and section in item:
            item[section] = api_items
            found = True
            break
    if not found:
        target.append({section: api_items})

    # Format and replace the nav in the raw text
    formatted = f"nav = {_format_nav_value(py_nav, 0)}"
    match = re.search(r"^nav\s*=\s*\[", raw, re.MULTILINE)
    if match is None:
        raise RuntimeError("Could not find 'nav' in TOML file")
    bracket_pos = raw.index("[", match.start())
    end_pos = _find_bracket_end(raw, bracket_pos)
    toml_path.write_text(raw[: match.start()] + formatted + raw[end_pos + 1 :])
    print(f"Updated {section!r} nav in {toml_path}")


# ---- Main ----


def main(argv: list[str] | None = None) -> None:
    """Generate API docs and update nav."""
    parser = argparse.ArgumentParser(
        description="Generate API doc stubs and update zensical.toml nav.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: cwd)",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        help="Source directory containing packages (default: ROOT/src)",
    )
    parser.add_argument(
        "--api-dir",
        type=Path,
        default=None,
        help="Output directory for API docs (default: ROOT/docs/api)",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Dotted namespace to exclude (repeatable)",
    )
    parser.add_argument(
        "--section",
        default="API Reference",
        help="Nav section name in zensical.toml (default: 'API Reference')",
    )
    parser.add_argument(
        "--parent",
        default=None,
        help="Parent nav section to nest under (e.g. 'pymmcore-plus')",
    )
    parser.add_argument(
        "--options",
        type=json.loads,
        default=None,
        help="JSON-formatted mkdocstrings options override",
    )
    parser.add_argument(
        "--dedicated",
        action="append",
        default=[],
        help="Fully qualified object to give its own page (repeatable)",
    )
    opts = parser.parse_args(argv)

    root: Path = opts.root.resolve()
    src_dir: Path = (opts.src or root / "src").resolve()
    docs_dir: Path = root / "docs"
    api_dir: Path = (opts.api_dir or docs_dir / "api").resolve()
    toml_path: Path = root / "zensical.toml"
    section: str = opts.section
    skip: set[str] = set(opts.skip)
    options: dict[str, Any] = (
        opts.options if opts.options is not None else DEFAULT_OPTIONS
    )

    # Resolve dedicated pages: map fqn -> output path, compute filters
    dedicated_paths: dict[str, Path] = {}
    filters: list[str] = []
    for fqn in opts.dedicated:
        parent_ns, obj_name = fqn.rsplit(".", 1)
        dedicated_paths[fqn] = api_dir / parent_ns.replace(".", "/") / f"{obj_name}.md"
        filters.append(f"!^{obj_name}$")

    # Save pre-existing dedicated pages before cleanup
    saved: dict[Path, str] = {}
    for path in dedicated_paths.values():
        if path.exists():
            saved[path] = path.read_text()

    # Clean existing API subdirectories, preserving top-level index.md
    if api_dir.exists():
        for child in api_dir.iterdir():
            if child.name == "index.md":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    # Find packages directly in src_dir
    for child in sorted(src_dir.iterdir()):
        if not child.is_dir() or not (child / "__init__.py").exists():
            continue
        namespace = child.name
        generate_docs(
            child, api_dir / namespace, namespace, skip, options, filters or None
        )
        print(f"  {namespace}/")

    # Restore or create dedicated pages
    for fqn, path in dedicated_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path in saved:
            path.write_text(saved[path])
            print(f"  dedicated (preserved): {fqn}")
        else:
            path.write_text(_make_stub(fqn, {}))
            print(f"  dedicated (created): {fqn}")

    print(f"\nAPI docs generated in {api_dir}")
    update_nav(toml_path, api_dir, docs_dir, section, parent=opts.parent)


if __name__ == "__main__":
    main()
