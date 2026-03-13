"""Config models for Micro-Manager configuration files (slotted dataclasses)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from ._primitives import PropertySetting, dataclass_to_dict

if TYPE_CHECKING:
    from collections.abc import Container

    from .pymmcore import _CoreProtocol

SCHEMA_URL_BASE = "https://micro-manager.org"

_LABEL_PATTERN = re.compile(r"^[^,]+$")


@dataclass(slots=True)
class PropertyValue:
    """A property-value pair for device settings.

    Note that ``device`` is not specified here — this object is always a member
    of a properties list on a specific device.
    """

    property: str
    value: str

    def __post_init__(self) -> None:
        self.value = str(self.value)

    @classmethod
    def from_dict(cls, data: Any) -> PropertyValue:
        """Create from a dict, tuple/list, or existing instance."""
        if isinstance(data, cls):
            return data
        if isinstance(data, (list, tuple)):
            return cls(property=str(data[0]), value=str(data[1]))
        return cls(property=data["property"], value=str(data["value"]))


@dataclass(slots=True)
class Device:
    """A hardware device to load from an adapter library."""

    label: str
    library: str
    name: str
    pre_init_properties: list[PropertyValue] = field(default_factory=list)
    post_init_properties: list[PropertyValue] = field(default_factory=list)
    delay_ms: float | None = None
    focus_direction: Literal[-1, 0, 1] | None = None
    state_labels: dict[str, str] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("Device label cannot be empty.")
        if not _LABEL_PATTERN.match(self.label):
            raise ValueError(
                f"Device label must match pattern '^[^,]+$': {self.label!r}"
            )
        if self.label.lower() == "core":
            raise ValueError(
                "The label 'Core' is reserved for the Micro-Manager Core device."
            )

        modified = 0
        if self.focus_direction is not None:
            modified += 1
        if self.state_labels:
            modified += 1
        if self.children:
            modified += 1
        if modified > 1:
            raise ValueError(
                "Only one of the following fields may be set: "
                "focus_direction, state_labels, children"
            )

    @classmethod
    def from_dict(cls, data: Any) -> Device:
        """Create from a dict, tuple/list, or existing instance."""
        if isinstance(data, cls):
            return data
        if isinstance(data, (list, tuple)):
            return cls(label=str(data[0]), library=str(data[1]), name=str(data[2]))
        return cls(
            label=data["label"],
            library=data["library"],
            name=data["name"],
            pre_init_properties=[
                PropertyValue.from_dict(p) for p in data.get("pre_init_properties", [])
            ],
            post_init_properties=[
                PropertyValue.from_dict(p) for p in data.get("post_init_properties", [])
            ],
            delay_ms=data.get("delay_ms"),
            focus_direction=data.get("focus_direction"),
            state_labels=dict(data.get("state_labels", {})),
            children=list(data.get("children", [])),
        )


@dataclass(slots=True)
class Configuration:
    """A named group of property settings (a preset)."""

    name: str
    settings: list[PropertySetting] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Any) -> Configuration:
        """Create from a dict or existing instance."""
        if isinstance(data, cls):
            return data
        return cls(
            name=data["name"],
            settings=[PropertySetting.from_dict(s) for s in data.get("settings", [])],
        )


@dataclass(slots=True)
class ConfigGroup:
    """A group of configuration presets."""

    name: str
    configurations: list[Configuration] = field(default_factory=list)

    def get_configuration(self, name: str) -> Configuration | None:
        """Return the configuration with the given name, if it exists."""
        for config in self.configurations:
            if config.name == name:
                return config
        return None

    @classmethod
    def from_dict(cls, data: Any) -> ConfigGroup:
        """Create from a dict or existing instance."""
        if isinstance(data, cls):
            return data
        return cls(
            name=data["name"],
            configurations=[
                Configuration.from_dict(c) for c in data.get("configurations", [])
            ],
        )


@dataclass(slots=True)
class PixelSizeConfiguration(Configuration):
    """Pixel size calibration configuration."""

    pixel_size_um: float = 0.0
    affine_matrix: tuple[float, float, float, float, float, float] | None = None
    dxdz: float | None = None
    dydz: float | None = None
    optimal_z_um: float | None = None

    def __post_init__(self) -> None:
        if self.affine_matrix is not None and len(self.affine_matrix) != 6:
            raise ValueError(
                f"affine_matrix must have exactly 6 elements, "
                f"got {len(self.affine_matrix)}"
            )

    @classmethod
    def from_dict(cls, data: Any) -> PixelSizeConfiguration:
        """Create from a dict or existing instance."""
        if isinstance(data, cls):
            return data
        affine = data.get("affine_matrix")
        return cls(
            name=data["name"],
            settings=[PropertySetting.from_dict(s) for s in data.get("settings", [])],
            pixel_size_um=data.get("pixel_size_um", 0.0),
            affine_matrix=tuple(affine) if affine is not None else None,  # type: ignore[arg-type]
            dxdz=data.get("dxdz"),
            dydz=data.get("dydz"),
            optimal_z_um=data.get("optimal_z_um"),
        )


@dataclass(slots=True)
class MMConfig:
    """Micro-Manager configuration file schema."""

    devices: list[Device] = field(default_factory=list)
    startup_configuration: list[PropertySetting] = field(default_factory=list)
    shutdown_configuration: list[PropertySetting] = field(default_factory=list)
    configuration_groups: list[ConfigGroup] = field(default_factory=list)
    pixel_size_configurations: list[PixelSizeConfiguration] = field(
        default_factory=list
    )
    enable_parallel_device_initialization: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    schema_version: str = field(default="1.0", init=False, repr=False)

    def __post_init__(self) -> None:
        # Check for duplicate device labels
        labels = [d.label for d in self.devices]
        if len(labels) != len(set(labels)):
            dupes = {lbl for lbl in labels if labels.count(lbl) > 1}
            raise ValueError(
                f"Duplicate device labels found: {', '.join(sorted(dupes))}"
            )

        # Migrate System/Startup and System/Shutdown config groups
        remaining: list[ConfigGroup] = []
        for group in self.configuration_groups:
            if group.name == "System":
                for config in list(group.configurations):
                    if config.name == "Startup":
                        self.startup_configuration = _merge_settings(
                            self.startup_configuration, config.settings
                        )
                        group.configurations.remove(config)
                    elif config.name == "Shutdown":
                        self.shutdown_configuration = _merge_settings(
                            self.shutdown_configuration, config.settings
                        )
                        group.configurations.remove(config)
                if group.configurations:
                    remaining.append(group)
            else:
                remaining.append(group)
        self.configuration_groups = remaining

    # ---------------------- Getters ----------------------

    def get_device(self, label: str) -> Device | None:
        """Return the device with the given label, if it exists."""
        for device in self.devices:
            if device.label == label:
                return device
        return None

    def get_configuration_group(self, name: str) -> ConfigGroup | None:
        """Return the configuration group with the given name, if it exists."""
        for group in self.configuration_groups:
            if group.name == name:
                return group
        return None

    # ---------------------- Serialization ----------------------

    def to_dict(
        self,
        *,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """Serialize to a dictionary."""
        d = dataclass_to_dict(
            self, exclude_defaults=exclude_defaults, exclude_none=exclude_none
        )
        # schema_version is always present and always first
        d.pop("schema_version", None)
        return {"schema_version": "1.0", **d}

    def to_json(
        self,
        *,
        indent: int | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> str:
        """Serialize to a JSON string."""
        import json

        return json.dumps(
            self.to_dict(exclude_defaults=exclude_defaults, exclude_none=exclude_none),
            indent=indent,
        )

    def to_yaml(
        self,
        *,
        indent: int | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> str:
        """Serialize to a YAML string."""
        import yaml

        return yaml.safe_dump(
            self.to_dict(exclude_defaults=exclude_defaults, exclude_none=exclude_none),
            indent=indent,
            sort_keys=False,
        )

    def to_cfg(self) -> str:
        """Serialize to legacy Micro-Manager .cfg format."""
        from .conversion import iter_mm_cfg_lines

        return "\n".join(iter_mm_cfg_lines(self))

    # ---------------------- I/O ----------------------

    def write_file(
        self,
        filename: str | Path,
        indent: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Write configuration to a file (.json, .yaml, .yml, or .cfg)."""
        output = Path(filename)
        if output.suffix == ".json":
            string = self.to_json(indent=indent, **kwargs) + "\n"
        elif output.suffix in {".yaml", ".yml"}:
            string = self.to_yaml(indent=indent, **kwargs)
        elif output.suffix == ".cfg":
            string = self.to_cfg()
        else:
            raise NotImplementedError(
                f"Unsupported output file format: {output.suffix}"
            )
        output.write_text(string, encoding="utf-8")

    @classmethod
    def from_file(cls, filename: str | Path) -> MMConfig:
        """Load a configuration from a .json, .yaml, .yml, or .cfg file."""
        fpath = Path(filename)
        if fpath.suffix == ".cfg":
            from .conversion import read_mm_cfg_file

            return read_mm_cfg_file(fpath)
        if fpath.suffix == ".json":
            import json

            data = json.loads(fpath.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        if fpath.suffix in {".yaml", ".yml"}:
            import yaml

            data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        raise NotImplementedError(f"Unsupported input file format: {fpath.suffix}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MMConfig:
        """Create from a dictionary (e.g. parsed JSON/YAML)."""
        return cls(
            devices=[Device.from_dict(d) for d in data.get("devices", [])],
            startup_configuration=[
                PropertySetting.from_dict(s)
                for s in data.get("startup_configuration", [])
            ],
            shutdown_configuration=[
                PropertySetting.from_dict(s)
                for s in data.get("shutdown_configuration", [])
            ],
            configuration_groups=[
                ConfigGroup.from_dict(g) for g in data.get("configuration_groups", [])
            ],
            pixel_size_configurations=[
                PixelSizeConfiguration.from_dict(p)
                for p in data.get("pixel_size_configurations", [])
            ],
            enable_parallel_device_initialization=data.get(
                "enable_parallel_device_initialization"
            ),
            extra=data.get("extra", {}),
        )

    def load_in_pymmcore(
        self, core: _CoreProtocol, *, exclude_devices: Container[str] = ()
    ) -> None:
        """Apply the configuration to a Micro-Manager core instance."""
        from .pymmcore import load_system_configuration

        load_system_configuration(core, self, exclude_devices=exclude_devices)


def _merge_settings(
    target: list[PropertySetting], source: list[PropertySetting]
) -> list[PropertySetting]:
    """Merge settings, source overwrites target on (device, property) key."""
    output = {setting.as_tuple()[:2]: setting for setting in target}
    for setting in source:
        output[setting.as_tuple()[:2]] = setting
    return list(output.values())
