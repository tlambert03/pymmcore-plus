from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import pymmcore_plus
from mmcore_schema import DeviceType, FocusDirection, PropertySetting, PropertyType
from mmcore_schema.state import (
    ConfigGroup,
    ConfigPreset,
    DeviceInfo,
    PixelSizePreset,
    PropertyInfo,
    SystemState,
)
from pymmcore_plus.core_io import (
    apply_config,
    read_config_group,
    read_config_groups,
    read_device_info,
    read_devices,
    read_pixel_size_preset,
    read_pixel_size_presets,
    read_properties,
    read_property_info,
    read_system_state,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def demo_core() -> Iterator[pymmcore_plus.CMMCorePlus]:
    core = pymmcore_plus.CMMCorePlus()
    if not core.getDeviceAdapterSearchPaths():
        pytest.fail("To run tests, please install MM with `mmcore install`")
    core.loadSystemConfiguration()
    yield core


# --------------- Property reads ---------------


def test_read_property_info(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    info = read_property_info(demo_core, "Camera", "Binning")
    assert isinstance(info, PropertyInfo)
    assert info.name == "Binning"
    assert isinstance(info.value, str)
    assert isinstance(info.data_type, PropertyType)
    assert isinstance(info.is_read_only, bool)
    assert isinstance(info.allowed_values, tuple)
    assert len(info.allowed_values) > 0


def test_read_property_info_with_limits(
    demo_core: pymmcore_plus.CMMCorePlus,
) -> None:
    info = read_property_info(demo_core, "Camera", "Exposure")
    assert info.limits is not None
    assert len(info.limits) == 2
    assert info.limits[0] < info.limits[1]


def test_read_properties(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    props = read_properties(demo_core, "Camera")
    assert isinstance(props, tuple)
    assert len(props) > 0
    assert all(isinstance(p, PropertyInfo) for p in props)
    names = {p.name for p in props}
    assert "Binning" in names
    assert "Exposure" in names


# --------------- Device reads ---------------


def test_read_device_info(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    info = read_device_info(demo_core, "Camera")
    assert isinstance(info, DeviceInfo)
    assert info.label == "Camera"
    assert info.library == "DemoCamera"
    assert info.type == DeviceType.Camera
    assert len(info.properties) > 0


def test_read_device_info_stage(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    info = read_device_info(demo_core, "Z")
    assert info.type == DeviceType.Stage
    assert isinstance(info.focus_direction, FocusDirection)


def test_read_device_info_state(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    info = read_device_info(demo_core, "Objective")
    assert info.type == DeviceType.State
    assert len(info.state_labels) > 0


def test_read_device_info_hub(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    info = read_device_info(demo_core, "DHub")
    assert info.type == DeviceType.Hub
    assert len(info.child_names) > 0


def test_read_devices(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    devices = read_devices(demo_core)
    assert isinstance(devices, tuple)
    assert len(devices) > 0
    assert all(isinstance(d, DeviceInfo) for d in devices)
    labels = {d.label for d in devices}
    assert "Camera" in labels
    assert "Core" in labels


# --------------- Config group reads ---------------


def test_read_config_group(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    group = read_config_group(demo_core, "Channel")
    assert isinstance(group, ConfigGroup)
    assert group.name == "Channel"
    assert len(group.presets) > 0
    for name, preset in group.presets.items():
        assert isinstance(preset, ConfigPreset)
        assert preset.name == name
        assert len(preset.settings) > 0
        assert all(isinstance(s, PropertyInfo) for s in preset.settings)


def test_read_config_groups(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    groups = read_config_groups(demo_core)
    assert isinstance(groups, tuple)
    assert len(groups) > 0
    names = {g.name for g in groups}
    assert "Channel" in names


# --------------- Pixel size reads ---------------


def test_read_pixel_size_preset(
    demo_core: pymmcore_plus.CMMCorePlus,
) -> None:
    configs = demo_core.getAvailablePixelSizeConfigs()
    if not configs:
        pytest.skip("No pixel size configs in demo config")
    preset = read_pixel_size_preset(demo_core, configs[0])
    assert isinstance(preset, PixelSizePreset)
    assert preset.name == configs[0]
    assert isinstance(preset.pixel_size_um, float)
    assert len(preset.affine) == 6


def test_read_pixel_size_presets(
    demo_core: pymmcore_plus.CMMCorePlus,
) -> None:
    presets = read_pixel_size_presets(demo_core)
    assert isinstance(presets, tuple)
    assert all(isinstance(p, PixelSizePreset) for p in presets)


# --------------- System state ---------------


def test_read_system_state(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    state = read_system_state(demo_core)
    assert isinstance(state, SystemState)

    # devices
    assert len(state.devices) > 0
    labels = {d.label for d in state.devices}
    assert "Camera" in labels
    assert "Core" in labels

    # config groups
    assert len(state.config_groups) > 0
    group_names = {g.name for g in state.config_groups}
    assert "Channel" in group_names

    # pixel size configs
    assert isinstance(state.pixel_size_configs, tuple)


# --------------- Apply ---------------


def test_apply_config(demo_core: pymmcore_plus.CMMCorePlus) -> None:
    group = read_config_group(demo_core, "Channel")
    preset_names = list(group.presets.keys())
    assert len(preset_names) >= 2

    apply_config(demo_core, "Channel", preset_names[1])
    assert demo_core.getCurrentConfig("Channel") == preset_names[1]

    apply_config(demo_core, "Channel", preset_names[0])
    assert demo_core.getCurrentConfig("Channel") == preset_names[0]


# --------------- Enum cross-equality with pymmcore-plus ---------------


def test_device_type_matches_pymmcore_plus(
    demo_core: pymmcore_plus.CMMCorePlus,
) -> None:
    """Ensure mmcore_schema DeviceType values match pymmcore DeviceType."""
    from pymmcore_plus.core._constants import DeviceType as PlusDT

    cam_info = read_device_info(demo_core, "Camera")
    assert cam_info.type == PlusDT.Camera
    assert int(cam_info.type) == int(PlusDT.Camera)
