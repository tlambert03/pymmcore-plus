from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from mmcore_schema import __main__

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("ext", [".json", ".yaml", ".cfg", ""])
def test_cli(
    cfg_file: Path,
    ext: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if ext:
        out_file = tmp_path / f"test{ext}"
        monkeypatch.setattr(sys, "argv", ["mmconfig", str(cfg_file), str(out_file)])
    else:
        monkeypatch.setattr(sys, "argv", ["mmconfig", str(cfg_file)])
    __main__.main()
    captured = capsys.readouterr()
    assert bool(captured.out) is bool(ext == "")
