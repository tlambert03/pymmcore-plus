from __future__ import annotations

import pytest

from mmcore_schema import MMConfig
from mmcore_schema._primitives import PropertySetting
from mmcore_schema.mmconfig import (
    ConfigGroup,
    Configuration,
    Device,
    PixelSizeConfiguration,
    PropertyValue,
)


def test_config() -> None:
    mm_config = MMConfig(
        devices=[
            Device(label="MyCam", library="DemoCamera", name="DCam"),
            Device(label="Dev", library="Lib", name="Name"),
        ],
        startup_configuration=[
            PropertySetting(device="Core", property="TimeoutMs", value="1000"),
            PropertySetting(device="Core", property="Camera", value="MyCam"),
        ],
        configuration_groups=[
            ConfigGroup(
                name="SomeGroup",
                configurations=[
                    Configuration(
                        name="SomeConfig",
                        settings=[
                            PropertySetting(
                                device="Camera",
                                property="PixelSize",
                                value="1.0",
                            ),
                            PropertySetting(
                                device="Camera", property="Binning", value="2"
                            ),
                        ],
                    )
                ],
            )
        ],
    )
    assert mm_config.startup_configuration
    assert not mm_config.shutdown_configuration

    my_cam = mm_config.get_device("MyCam")
    assert my_cam is not None
    assert my_cam.label == "MyCam"
    assert mm_config.get_device("NotMyCam") is None

    cfg_grp = mm_config.get_configuration_group("SomeGroup")
    assert cfg_grp is not None
    assert mm_config.get_configuration_group("NotSomeGroup") is None

    cfg = cfg_grp.get_configuration("SomeConfig")
    assert cfg is not None
    assert cfg_grp.get_configuration("NotSomeConfig") is None


def test_from_dict() -> None:
    """Test MMConfig.from_dict with flexible input (tuples, dicts)."""
    mm_config = MMConfig.from_dict(
        {
            "devices": [
                {"label": "MyCam", "library": "DemoCamera", "name": "DCam"},
                ("Dev", "Lib", "Name"),
            ],
            "startup_configuration": [
                {"device": "Core", "property": "TimeoutMs", "value": 1000},
                ("Core", "Camera", "MyCam"),
            ],
            "configuration_groups": [
                {
                    "name": "SomeGroup",
                    "configurations": [
                        {
                            "name": "SomeConfig",
                            "settings": [
                                {
                                    "device": "Camera",
                                    "property": "PixelSize",
                                    "value": "1.0",
                                },
                                ("Camera", "Binning", 2),
                            ],
                        }
                    ],
                }
            ],
        }
    )
    assert len(mm_config.devices) == 2
    assert mm_config.devices[1].label == "Dev"
    assert mm_config.startup_configuration[0].value == "1000"  # coerced to str


def test_config_to_dict() -> None:
    mm_config = MMConfig(
        devices=[Device(label="MyCam", library="DemoCamera", name="DCam")],
    )
    dumped = mm_config.to_dict()
    assert "schema_version" in dumped
    assert dumped["schema_version"] == "1.0"


def test_config_to_dict_exclude_defaults() -> None:
    mm_config = MMConfig(
        devices=[Device(label="MyCam", library="DemoCamera", name="DCam")],
    )
    dumped = mm_config.to_dict(exclude_defaults=True)
    # schema_version is always present
    assert "schema_version" in dumped
    # empty lists should be excluded
    assert "startup_configuration" not in dumped
    assert "shutdown_configuration" not in dumped
    assert "configuration_groups" not in dumped
    # devices is not default (non-empty)
    assert "devices" in dumped


def test_special_groups() -> None:
    mm_config = MMConfig.from_dict(
        {
            "devices": [
                {"label": "MyCam", "library": "DemoCamera", "name": "DCam"},
            ],
            "configuration_groups": [
                {
                    "name": "System",
                    "configurations": [
                        {
                            "name": "Startup",
                            "settings": [("MyCam", "Binning", 2)],
                        },
                        {
                            "name": "Shutdown",
                            "settings": [("MyCam", "Binning", 2)],
                        },
                    ],
                }
            ],
        }
    )
    assert mm_config.startup_configuration
    assert mm_config.shutdown_configuration
    # System group was consumed (no remaining configurations)
    assert not any(g.name == "System" for g in mm_config.configuration_groups)


def test_config_errors() -> None:
    # duplicate device labels
    with pytest.raises(ValueError, match="Duplicate device label"):
        MMConfig(
            devices=[
                Device(label="Dev", library="Lib", name="Name"),
                Device(label="Dev", library="Lib", name="Name"),
            ]
        )

    # "Core" label
    with pytest.raises(ValueError, match="The label 'Core' is reserved"):
        Device(label="Core", library="DemoCamera", name="DCam")
    with pytest.raises(ValueError, match="The label 'Core' is reserved"):
        Device(label="core", library="DemoCamera", name="DCam")

    # empty label
    with pytest.raises(ValueError, match="cannot be empty"):
        Device(label="", library="DemoCamera", name="DCam")

    # comma in label
    with pytest.raises(ValueError, match="pattern"):
        Device(label="My,Device", library="DemoCamera", name="DCam")

    # mutually exclusive fields
    with pytest.raises(ValueError, match="Only one of the following"):
        Device(
            label="MyCam",
            library="DemoCamera",
            name="DCam",
            focus_direction=1,
            state_labels={"0": "State 0", "1": "State 1"},
        )
    with pytest.raises(ValueError, match="Only one of the following"):
        Device(
            label="MyCam",
            library="DemoCamera",
            name="DCam",
            state_labels={"0": "State 0"},
            children=["A", "B"],
        )


def test_property_setting_coercion() -> None:
    s = PropertySetting(device="Dev", property="Prop", value=42)  # type: ignore[arg-type]
    assert s.value == "42"
    assert isinstance(s.value, str)
    assert s.as_tuple() == ("Dev", "Prop", "42")


def test_property_value_coercion() -> None:
    pv = PropertyValue(property="Gain", value=100)  # type: ignore[arg-type]
    assert pv.value == "100"


def test_pixel_size_configuration() -> None:
    psc = PixelSizeConfiguration(
        name="Res20x",
        pixel_size_um=0.5,
        affine_matrix=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    )
    assert psc.pixel_size_um == 0.5
    assert psc.affine_matrix is not None
    assert len(psc.affine_matrix) == 6


def test_pixel_size_configuration_bad_affine() -> None:
    with pytest.raises(ValueError, match="exactly 6 elements"):
        PixelSizeConfiguration(
            name="Bad",
            affine_matrix=(1.0, 0.0, 0.0),  # type: ignore[arg-type]
        )
