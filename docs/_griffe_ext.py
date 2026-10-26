"""Griffe extension to render `pymmcore.CMMCore` from its `.pyi` stubs.

Use with `allow_inspection: false` and `preload_modules: [pymmcore]`. Works around
two griffe behaviors with stub-only packages (see mkdocstrings/griffe#447):

1. Methods defined *only* as `@overload`s in a stub are dropped when the stub class
   is merged into itself, so we promote them to real functions.
2. Stub-only members are marked `runtime=False`, which hides them from
   `from pymmcore import *` (used by `pymmcore_plus._pymmcore`), so CMMCorePlus
   would lose its base class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import griffe


class PymmcoreStubs(griffe.Extension):
    def on_class_members(self, *, cls: griffe.Class, **kwargs: Any) -> None:
        if cls.module.package.name != "pymmcore":
            return
        filepath = cls.module.filepath
        if not (isinstance(filepath, Path) and filepath.suffix == ".pyi"):
            return
        for name, overloads in list(cls.overloads.items()):
            if not overloads or name in cls.members:
                continue
            first = overloads[0]
            func = griffe.Function(
                name,
                lineno=first.lineno,
                endlineno=overloads[-1].endlineno,
                parameters=first.parameters,
                returns=first.returns,
                runtime=first.runtime,
                analysis="static",
            )
            if doc_src := next((o.docstring for o in overloads if o.docstring), None):
                func.docstring = griffe.Docstring(
                    doc_src.value,
                    lineno=doc_src.lineno,
                    endlineno=doc_src.endlineno,
                    parent=func,
                )
            cls.set_member(name, func)
            func.overloads = overloads
            del cls.overloads[name]

    def on_package(self, *, pkg: griffe.Module, **kwargs: Any) -> None:
        if pkg.name == "pymmcore":
            for member in pkg.members.values():
                if not member.is_alias:
                    member.runtime = True
