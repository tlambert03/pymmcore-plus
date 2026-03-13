from __future__ import annotations

from pathlib import Path

import pytest

CONFIGS = Path(__file__).parent / "configs"
CFG_FILES = sorted(CONFIGS.glob("*.cfg"))


@pytest.fixture(params=CFG_FILES, ids=lambda x: x.stem)
def cfg_file(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[return-value]
