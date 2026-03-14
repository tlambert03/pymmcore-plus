from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mmcore_schema import MMConfig
from mmcore_schema._conversion import read_mm_cfg_file

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("ext", [".json", ".yaml", ".cfg"])
def test_read_cfg(cfg_file: Path, tmp_path: Path, ext: str) -> None:
    mm_cfg = read_mm_cfg_file(cfg_file)
    assert isinstance(mm_cfg, MMConfig)

    out_file = tmp_path / f"test{ext}"
    mm_cfg.write_file(out_file)
    assert out_file.exists()


def test_round_trip_json(cfg_file: Path, tmp_path: Path) -> None:
    original = read_mm_cfg_file(cfg_file)

    json_file = tmp_path / "test.json"
    original.write_file(json_file, indent=2)

    reloaded = MMConfig.from_file(json_file)
    assert len(reloaded.devices) == len(original.devices)
    assert len(reloaded.configuration_groups) == len(original.configuration_groups)
    assert len(reloaded.pixel_size_configurations) == len(
        original.pixel_size_configurations
    )


def test_round_trip_yaml(cfg_file: Path, tmp_path: Path) -> None:
    original = read_mm_cfg_file(cfg_file)

    yaml_file = tmp_path / "test.yaml"
    original.write_file(yaml_file)

    reloaded = MMConfig.from_file(yaml_file)
    assert len(reloaded.devices) == len(original.devices)
    assert len(reloaded.configuration_groups) == len(original.configuration_groups)


def test_round_trip_cfg(cfg_file: Path, tmp_path: Path) -> None:
    original = read_mm_cfg_file(cfg_file)

    cfg_out = tmp_path / "test.cfg"
    original.write_file(cfg_out)

    reloaded = MMConfig.from_file(cfg_out)
    assert len(reloaded.devices) == len(original.devices)
    # Config groups may differ due to System/Startup/Shutdown merge
    # but total settings should be preserved
    orig_settings = sum(
        len(c.settings) for g in original.configuration_groups for c in g.configurations
    )
    reload_settings = sum(
        len(c.settings) for g in reloaded.configuration_groups for c in g.configurations
    )
    assert reload_settings == orig_settings


def test_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="Unsupported"):
        MMConfig.from_file(tmp_path / "test.xml")
    cfg = MMConfig()
    with pytest.raises(NotImplementedError, match="Unsupported"):
        cfg.write_file(tmp_path / "test.xml")
