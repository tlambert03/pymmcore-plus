"""State models representing a snapshot of a running Micro-Manager system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .enums import DeviceType, FocusDirection, PropertyType

if TYPE_CHECKING:
    from ._primitives import AffineTuple, PropertySetting


@dataclass(slots=True)
class PropertyInfo:
    """Runtime information about a single device property."""

    name: str
    value: str = ""
    data_type: PropertyType = PropertyType.Undef
    is_read_only: bool = False
    is_pre_init: bool = False
    allowed_values: tuple[str, ...] = ()
    limits: tuple[float, float] | None = None
    device_label: str = ""
    device_type: DeviceType = DeviceType.Unknown
    sequence_max_length: int = 0


@dataclass(slots=True)
class DeviceInfo:
    """Runtime information about a loaded device."""

    label: str
    library: str = ""
    name: str = ""
    description: str = ""
    type: DeviceType = DeviceType.Unknown
    properties: tuple[PropertyInfo, ...] = ()
    parent_label: str = ""
    # type-specific fields (at most one populated)
    state_labels: tuple[str, ...] = ()
    focus_direction: FocusDirection = FocusDirection.Unknown
    child_names: tuple[str, ...] = ()


@dataclass(slots=True)
class ConfigPreset:
    """A named preset within a config group."""

    name: str
    settings: list[PropertyInfo] = field(default_factory=list)


@dataclass(slots=True)
class ConfigGroup:
    """A group of configuration presets (state view)."""

    name: str
    presets: dict[str, ConfigPreset] = field(default_factory=dict)
    is_channel_group: bool = False

    @property
    def is_system_group(self) -> bool:
        return self.name.lower() == "system"


@dataclass(slots=True)
class PixelSizePreset:
    """A pixel size preset with calibration data."""

    name: str
    settings: list[PropertySetting] = field(default_factory=list)
    pixel_size_um: float = 0.0
    affine: AffineTuple = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    dxdz: float = 0.0
    dydz: float = 0.0
    optimal_z_um: float = 0.0


@dataclass(slots=True)
class SystemState:
    """Complete snapshot of a running system."""

    devices: tuple[DeviceInfo, ...] = ()
    config_groups: tuple[ConfigGroup, ...] = ()
    pixel_size_configs: tuple[PixelSizePreset, ...] = ()
