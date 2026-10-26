"""Generate docs content for pymmcore-plus.  Run before building the docs.

Writes (gitignored) files into docs/_generated/:

- cmmcoreplus_table.md    filterable table of every CMMCorePlus method
- cmmcoreplus_members.md  `:::` blocks for every method, grouped by category
- cli.md                  reference for the `mmcore` command line tool
- cli_logs.md             `mmcore logs --help` output
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import griffe
import pymmcore

from pymmcore_plus import CMMCorePlus

DOCS = Path(__file__).parent
OUT = DOCS / "_generated"
sys.path.insert(0, str(DOCS))
from _griffe_ext import PymmcoreStubs  # noqa: E402

SKIP = {"this", "thisown"}  # SWIG internals

# (category, pattern) -- first match wins, so order matters.
CATEGORIES: list[tuple[str, str]] = [
    (
        "Acquisition engine & events",
        r"^(mda|run_mda|register_mda_engine|events|registerCallback|setContext)$",
    ),
    ("Pumps", r"[Pp]ump"),
    ("Galvos", r"Galvo"),
    ("SLMs", r"SLM"),
    ("Serial ports", r"Serial"),
    ("Pixel size", r"PixelSize|MagnificationFactor"),
    (
        "Hardware sequencing",
        r"Sequence(?!Acquisition|Running)|Sequenceable|canSequenceEvents",
    ),
    (
        "Images & buffer",
        r"SequenceAcquisition|isSequenceRunning|Buffer|^snap|[Ii]mage(?!Processor)|popNext|getNBeforeLast|getRemainingImageCount|getTags$",
    ),
    (
        "Cameras",
        r"Camera|Exposure|Binning|ROI|BytesPerPixel|NumberOfComponents|ImageProcessor",
    ),
    ("Autofocus", r"AutoFocus|ContinuousFocus|FocusScore|fullFocus|incrementalFocus"),
    (
        "Stages",
        r"Position|XYStage|Stage|Origin|^home$|^stop$|FocusDevice|FocusDirection",
    ),
    ("Shutters", r"Shutter"),
    (
        "Config groups & presets",
        r"Config(?!uration)|ConfigGroup|isGroupDefined|[Cc]hannelGroup",
    ),
    ("State devices", r"State(?!Cache)|Label|NumberOfStates|[Oo]bjective"),
    (
        "System state & configuration files",
        r"[Ss]ystem(?!Busy)|^state$|^describe$|^reset$|Version",
    ),
    ("Properties", r"Property|Properties"),
    ("Devices", r"Device|Adapter|Library|[Ii]nitializ|Busy|waitFor|Timeout|Delay"),
    ("Logging & errors", r"[Ll]og|Error|Feature|[Dd]ebug|[Ss]tderr"),
    ("Other", r""),
]

ORIGIN_ICON = {"added": "\u2728", "overridden": "\u2795", "inherited": ""}
ORIGIN_TITLE = {
    "added": "Only in CMMCorePlus",
    "overridden": "Overridden by CMMCorePlus",
    "inherited": "Inherited from pymmcore.CMMCore",
}
WHY_OVERRIDE = re.compile(r"\*\*Why Override\?\*\*\s*(.+?)(?:\n\s*\n|$)", re.DOTALL)


def _load() -> griffe.Class:
    loader = griffe.GriffeLoader(
        extensions=griffe.load_extensions(PymmcoreStubs()),
        allow_inspection=False,
        search_paths=[str(DOCS.parent / "src"), *sys.path],
    )
    loader.load("pymmcore")
    plus = loader.load("pymmcore_plus")
    loader.resolve_aliases(implicit=False, external=None)
    return plus["CMMCorePlus"]  # type: ignore[return-value]


def _category(name: str) -> str:
    return next(cat for cat, pattern in CATEGORIES if re.search(pattern, name))


def _first_paragraph(text: str) -> str:
    para = text.strip().split("\n\n")[0]
    return " ".join(line.strip() for line in para.splitlines())


def _inline_html(text: str) -> str:
    """Escape text, drop Markdown link syntax, and render `code` spans."""
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]|\[([^\]]+)\]\([^)]*\)", r"\1\2", text)
    parts = re.split(r"`([^`]+)`", html.escape(text, quote=False))
    return "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts))


def _signature(obj: griffe.Object) -> str:
    if not isinstance(obj, griffe.Function):
        return ""
    params = [p.name for p in obj.parameters if p.name != "self"]
    sig = f"({', '.join(params)})"
    if n := len(obj.overloads or ()):
        sig += f" <small>({n} overloads)</small>"
    return sig


def method_rows() -> list[dict[str, str]]:
    cls = _load()
    base_names = set(pymmcore.CMMCore.__dict__)
    plus_names = set(CMMCorePlus.__dict__)
    rows = []
    for name in sorted((base_names | plus_names) - SKIP, key=str.lower):
        if name.startswith("_"):
            continue
        origin = (
            "overridden"
            if name in base_names and name in plus_names
            else "added"
            if name in plus_names
            else "inherited"
        )
        member = cls.all_members.get(name)
        obj = member.final_target if member is not None and member.is_alias else member
        doc = obj.docstring.value if obj is not None and obj.docstring else ""
        runtime = getattr(CMMCorePlus, name, None)
        deprecated = bool(getattr(runtime, "__deprecated__", None)) or (
            "deprecated" in doc.lower()[:300]
        )
        why = WHY_OVERRIDE.search(doc)
        rows.append(
            {
                "name": name,
                "origin": origin,
                "category": _category(name),
                "deprecated": "true" if deprecated else "false",
                "summary": _first_paragraph(WHY_OVERRIDE.sub("", doc)),
                "why": " ".join(why.group(1).split()) if why else "",
                "signature": _signature(obj) if obj is not None else "",
                "kind": obj.kind.value if obj is not None else "attribute",
            }
        )
    return rows


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def write_table(rows: list[dict[str, str]]) -> str:
    out = [
        '<table class="pymm-explorer" data-object="pymmcore_plus.CMMCorePlus">',
        "<thead><tr><th>Method</th><th>Origin</th><th>Category</th>"
        "<th>Description</th></tr></thead>",
        "<tbody>",
    ]
    for r in rows:
        anchor = f"pymmcore_plus.CMMCorePlus.{r['name']}"
        title = ORIGIN_TITLE[r["origin"]]
        if r["why"]:
            title += f" — {r['why']}"
        origin = (
            f'<span class="pymm-origin pymm-origin--{r["origin"]}" '
            f'title="{html.escape(title)}">{ORIGIN_ICON[r["origin"]]}</span>'
        )
        sig = (
            f'<span class="pymm-sig">{r["signature"]}</span>' if r["signature"] else ""
        )
        out.append(
            f'<tr data-origin="{r["origin"]}" data-category="{_slug(r["category"])}" '
            f'data-deprecated="{r["deprecated"]}">'
            f'<td><a href="#{anchor}"><code>{r["name"]}</code></a>{sig}</td>'
            f"<td>{origin}</td>"
            f'<td><a href="#cmmcoreplus-{_slug(r["category"])}">'
            f"{r['category']}</a></td>"
            f"<td>{_inline_html(r['summary'])}</td></tr>"
        )
    out += ["</tbody>", "</table>", ""]
    return "\n".join(out)


def write_members(rows: list[dict[str, str]]) -> str:
    out: list[str] = []
    for category, _ in CATEGORIES:
        names = [r["name"] for r in rows if r["category"] == category]
        if not names:
            continue
        out += [f"## {category} {{#cmmcoreplus-{_slug(category)}}}", ""]
        for name in names:
            out += [
                f"::: pymmcore_plus.CMMCorePlus.{name}",
                "    options:",
                "      heading_level: 3",
                "      show_root_full_path: false",
                "",
            ]
    return "\n".join(out)


def write_cli() -> None:
    env = {**os.environ, "COLUMNS": "80", "NO_COLOR": "1", "TERM": "dumb"}
    bin_dir = str(Path(sys.executable).parent)
    typer = shutil.which("typer", path=bin_dir) or "typer"
    mmcore = shutil.which("mmcore", path=bin_dir) or "mmcore"
    md = subprocess.check_output(
        [typer, "pymmcore_plus._cli", "utils", "docs", "--name", "mmcore"],
        env=env,
        text=True,
        encoding="utf-8",
    )
    # drop the (dev) version from the CLI's description
    md = re.sub(r" \(v[^)]*\)", "", md, count=1)
    # demote headings so the page's own h1 stays the only h1
    md = re.sub(r"^(#+) ", lambda m: "#" + m.group(1) + " ", md, flags=re.MULTILINE)
    (OUT / "cli.md").write_text(md, encoding="utf-8")
    logs = subprocess.check_output(
        [mmcore, "logs", "--help"], env=env, text=True, encoding="utf-8"
    )
    (OUT / "cli_logs.md").write_text(
        f"```console\n$ mmcore logs --help\n{logs}```\n", encoding="utf-8"
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = method_rows()
    (OUT / "cmmcoreplus_table.md").write_text(write_table(rows), encoding="utf-8")
    (OUT / "cmmcoreplus_members.md").write_text(write_members(rows), encoding="utf-8")
    write_cli()
    counts = {o: sum(r["origin"] == o for r in rows) for o in ORIGIN_ICON}
    other = [r["name"] for r in rows if r["category"] == "Other"]
    print(f"CMMCorePlus: {len(rows)} members {counts}; uncategorized: {other}")


if __name__ == "__main__":
    main()
