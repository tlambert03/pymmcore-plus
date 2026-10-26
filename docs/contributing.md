# Contributing

Thanks for thinking of a way to help improve this library! Remember that
contributions come in all shapes and sizes beyond writing bug fixes.
Contributing to [documentation](#contributing-documentation), opening new
[issues](https://github.com/pymmcore-plus/pymmcore-plus/issues) for bugs, asking
for clarification on things you find unclear, and requesting new features, are
all super valuable contributions.

## Contributing Code

All development for this library happens in the
[pymmcore-plus/pymmcore-plus
](https://github.com/pymmcore-plus/pymmcore-plus) repo on GitHub. We recommend you work
with [uv](https://docs.astral.sh/uv/getting-started/installation/), but any virtual
environment manager should work.

Using `uv`:

```bash
git clone <your fork>
cd pymmcore-plus
uv sync
prek install  # or: pre-commit install
```

```sh
uv run pytest 
```

or activate the virtual environment (`source .venv/bin/activate` on
Linux/macOS, `.venv\Scripts\activate` on Windows) and run:

```bash
pytest
```

If using a different virtual environment manager (like conda) instead of uv,
you can install the dependencies with:

```bash
pip install -e . --group dev
```

> This requires a newer version of `pip` (>= 25.1) to work.

## Contributing Documentation

These docs are written in the `docs/` folder of this repository (and in
docstrings), but are published as part of the unified pymmcore-plus ecosystem
site, built by
[pymmcore-plus/pymmcore-plus.github.io](https://github.com/pymmcore-plus/pymmcore-plus.github.io).
See [How these docs work](../contributing/docs.md) for how to preview your
changes locally.

## Developing on Apple Silicon

To build a native version of the DemoCamera for local testing on apple silicon, you
can run the following command (you must have [homebrew](https://brew.sh) installed)

```shell
uv run mmcore build-dev
```

This will download the micro-manager repo, build it, and drop the DemoCamera and
Utilities devices into a folder in your pymmcore-plus install folder (by default
`~/Library/Application Support/pymmcore-plus/mm`).  This path is on the default
search path so you should be good to go.  You can confirm by running:

```py
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus()
core.loadSystemConfiguration()
core.snap()
```
