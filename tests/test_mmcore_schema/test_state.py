from __future__ import annotations

from mmcore_schema._primitives import dataclass_to_dict
from mmcore_schema.enums import DeviceType, FocusDirection, PropertyType
from mmcore_schema.state import (
    ConfigGroup,
    ConfigPreset,
    DeviceInfo,
    PixelSizePreset,
    PropertyInfo,
    SystemState,
)


def test_property_info() -> None:
    p = PropertyInfo(
        name="Gain",
        value="42",
        data_type=PropertyType.Integer,
        is_read_only=False,
        allowed_values=("0", "50", "100"),
        limits=(0.0, 100.0),
    )
    assert p.name == "Gain"
    assert p.data_type == PropertyType.Integer
    assert p.limits == (0.0, 100.0)


def test_device_info() -> None:
    d = DeviceInfo(
        label="Camera",
        library="DemoCamera",
        name="DCam",
        type=DeviceType.Camera,
        properties=(
            PropertyInfo(name="Exposure", value="10.0"),
            PropertyInfo(name="Binning", value="1"),
        ),
    )
    assert d.type == DeviceType.Camera
    assert len(d.properties) == 2


def test_config_preset() -> None:
    preset = ConfigPreset(
        name="DAPI",
        settings=[
            PropertyInfo(name="Label", device_label="Dichroic", value="400"),
        ],
    )
    assert preset.name == "DAPI"
    assert len(preset.settings) == 1


def test_config_group() -> None:
    group = ConfigGroup(
        name="Channel",
        presets={
            "DAPI": ConfigPreset(name="DAPI"),
            "FITC": ConfigPreset(name="FITC"),
        },
    )
    assert len(group.presets) == 2
    assert "DAPI" in group.presets


def test_pixel_size_preset() -> None:
    preset = PixelSizePreset(
        name="Res20x",
        pixel_size_um=0.5,
        affine=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    )
    assert preset.pixel_size_um == 0.5
    assert preset.affine == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    assert preset.name == "Res20x"
    assert isinstance(preset.settings, list)


def test_system_state() -> None:
    state = SystemState(
        devices=(
            DeviceInfo(label="Camera", type=DeviceType.Camera),
            DeviceInfo(
                label="Z",
                type=DeviceType.Stage,
                focus_direction=FocusDirection.TowardSample,
            ),
        ),
        config_groups=(ConfigGroup(name="Channel"),),
    )
    assert len(state.devices) == 2
    assert state.devices[1].focus_direction == FocusDirection.TowardSample


def test_state_serialization_round_trip() -> None:
    state = SystemState(
        devices=(
            DeviceInfo(
                label="Camera",
                library="DemoCamera",
                name="DCam",
                type=DeviceType.Camera,
                properties=(
                    PropertyInfo(
                        name="Exposure",
                        value="10.0",
                        data_type=PropertyType.Float,
                    ),
                ),
            ),
        ),
        config_groups=(
            ConfigGroup(
                name="Channel",
                presets={
                    "DAPI": ConfigPreset(
                        name="DAPI",
                        settings=[
                            PropertyInfo(
                                name="Label",
                                device_label="Dichroic",
                                value="400",
                            ),
                        ],
                    ),
                },
            ),
        ),
        pixel_size_configs=(PixelSizePreset(name="Res20x", pixel_size_um=0.5),),
    )

    d = dataclass_to_dict(state)
    assert isinstance(d, dict)
    assert len(d["devices"]) == 1
    assert d["devices"][0]["label"] == "Camera"
    assert d["devices"][0]["properties"][0]["name"] == "Exposure"
    assert len(d["config_groups"]) == 1
    assert "DAPI" in d["config_groups"][0]["presets"]
    assert len(d["pixel_size_configs"]) == 1


def test_enum_cross_equality() -> None:
    """Ensure IntEnum equality with pymmcore-plus enums (same int values)."""
    # DeviceType
    assert DeviceType.Camera == 2
    assert DeviceType.Hub == 15

    # PropertyType
    assert PropertyType.Undef == 0
    assert PropertyType.Float == 2

    # FocusDirection
    assert FocusDirection.Unknown == 0
    assert FocusDirection.TowardSample == 1
    assert FocusDirection.AwayFromSample == -1

    # Cross-package equality (same int value)
    assert DeviceType(2) == DeviceType.Camera
    assert FocusDirection(1) == FocusDirection.TowardSample
