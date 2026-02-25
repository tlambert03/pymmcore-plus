"""Griffe extension to replace SWIG docstrings with stub docstrings for pymmcore."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import griffe

if TYPE_CHECKING:
    from griffe import GriffeLoader, Module


def _extract_stub_docstrings(pyi_path: Path) -> dict[str, str]:
    """Parse a .pyi file and extract method docstrings from a class.

    Handles @overload methods (takes docstring from first overload) and
    regular methods alike.
    """
    source = pyi_path.read_text()
    tree = ast.parse(source)

    docstrings: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == "CMMCore"):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = item.name
            if name in docstrings:
                continue  # keep first occurrence (first @overload)
            doc = ast.get_docstring(item)
            if doc:
                docstrings[name] = doc
    return docstrings


class SWIGStubDocstrings(griffe.Extension):
    """Replace SWIG-generated docstrings with proper ones from .pyi stubs."""

    def on_package(
        self, *, pkg: Module, loader: GriffeLoader, **kwargs: object
    ) -> None:
        if pkg.name != "pymmcore":
            return

        # Find the .pyi stub file
        pkg_dir = Path(pkg.filepath).parent  # type: ignore[arg-type]
        pyi_path = pkg_dir / "__init__.pyi"
        if not pyi_path.exists():
            return

        # Extract all docstrings from the stub (including @overload methods)
        stub_docs = _extract_stub_docstrings(pyi_path)
        if not stub_docs:
            return

        # Find the runtime CMMCore class (in the SWIG submodule)
        for subpath in ("pymmcore_swig.CMMCore", "_pymmcore_swig.CMMCore"):
            try:
                swig_cls = pkg[subpath]
                break
            except KeyError:
                continue
        else:
            return

        # Replace SWIG docstrings with stub docstrings
        for name, doc in stub_docs.items():
            if name in swig_cls.members:
                member = swig_cls.members[name]
                member.docstring = griffe.Docstring(doc, parent=member)
