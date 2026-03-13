"""State models representing a snapshot of a running Micro-Manager system."""

from __future__ import annotations

import dataclasses
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._primitives import PropertySetting
from .enums import DeviceType, FocusDirection, PropertyType

if TYPE_CHECKING:
    from ._primitives import AffineTuple
    from pymmcore import CMMCore
    from pymmcore_nano import CMMCore


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

    @classmethod
    def from_core(
        cls,
        core: Any,
        device: str,
        prop: str,
        *,
        cached: bool = True,
        device_type: DeviceType | None = None,
    ) -> PropertyInfo:
        """Read information about a single device property from core."""
        try:
            value = (
                core.getPropertyFromCache(device, prop)
                if cached
                else core.getProperty(device, prop)
            )
        except Exception:
            value = ""

        limits: tuple[float, float] | None = None
        if core.hasPropertyLimits(device, prop):
            limits = (
                core.getPropertyLowerLimit(device, prop),
                core.getPropertyUpperLimit(device, prop),
            )

        seq_max = 0
        if core.isPropertySequenceable(device, prop):
            seq_max = core.getPropertySequenceMaxLength(device, prop)

        if device_type is None:
            device_type = DeviceType(int(core.getDeviceType(device)))

        return cls(
            name=prop,
            value=value or "",
            data_type=PropertyType(int(core.getPropertyType(device, prop))),
            is_read_only=core.isPropertyReadOnly(device, prop),
            is_pre_init=core.isPropertyPreInit(device, prop),
            allowed_values=core.getAllowedPropertyValues(device, prop),
            limits=limits,
            device_label=device,
            device_type=device_type,
            sequence_max_length=seq_max,
        )

    @classmethod
    def all_from_core(
        cls,
        core: Any,
        device: str,
        *,
        cached: bool = True,
        device_type: DeviceType | None = None,
    ) -> tuple[PropertyInfo, ...]:
        """Read all properties for a device."""
        if device_type is None:
            device_type = DeviceType(int(core.getDeviceType(device)))
        return tuple(
            cls.from_core(
                core, device, prop, cached=cached, device_type=device_type
            )
            for prop in core.getDevicePropertyNames(device)
        )


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

    @classmethod
    def from_core(
        cls,
        core: Any,
        label: str,
        *,
        cached: bool = True,
    ) -> DeviceInfo:
        """Read runtime information about a loaded device."""
        devtype = DeviceType(int(core.getDeviceType(label)))

        state_labels: tuple[str, ...] = ()
        focus_direction = FocusDirection.Unknown
        child_names: tuple[str, ...] = ()

        with suppress(RuntimeError):
            if devtype == DeviceType.Hub:
                child_names = core.getInstalledDevices(label)
            if devtype == DeviceType.State:
                state_labels = core.getStateLabels(label)
            elif devtype == DeviceType.Stage:
                with suppress(RuntimeError):
                    focus_direction = FocusDirection(
                        int(core.getFocusDirection(label))
                    )

        return cls(
            label=label,
            library=core.getDeviceLibrary(label),
            name=core.getDeviceName(label),
            description=core.getDeviceDescription(label),
            type=devtype,
            properties=PropertyInfo.all_from_core(
                core, label, cached=cached, device_type=devtype
            ),
            parent_label=core.getParentLabel(label),
            state_labels=state_labels,
            focus_direction=focus_direction,
            child_names=child_names,
        )

    @classmethod
    def all_from_core(
        cls,
        core: Any,
        *,
        cached: bool = True,
    ) -> tuple[DeviceInfo, ...]:
        """Read information about all loaded devices."""
        return tuple(
            cls.from_core(core, lbl, cached=cached)
            for lbl in core.getLoadedDevices()
        )

    @classmethod
    def available_from_core(cls, core: Any) -> tuple[DeviceInfo, ...]:
        """Read all available (not yet loaded) device adapters from core."""
        result: list[DeviceInfo] = []
        for library in core.getDeviceAdapterNames():
            dev_names = core.getAvailableDevices(library)
            types = core.getAvailableDeviceTypes(library)
            descriptions = core.getAvailableDeviceDescriptions(library)
            for dev_name, description, dev_type in zip(
                dev_names, descriptions, types, strict=False
            ):
                result.append(
                    cls(
                        label="",
                        name=dev_name,
                        library=library,
                        description=description,
                        type=DeviceType(dev_type),
                    )
                )
        return tuple(result)


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

    @classmethod
    def from_core(
        cls,
        core: Any,
        group_name: str,
        *,
        enrich: bool = False,
    ) -> ConfigGroup:
        """Read a single config group with all its presets from core.

        If *enrich* is True, each setting is populated with full property
        metadata (allowed values, limits, etc.).  Otherwise only *name*,
        *device_label*, and *value* are filled in.
        """
        presets: dict[str, ConfigPreset] = {}
        for preset_name in core.getAvailableConfigs(group_name):
            cfg = core.getConfigData(group_name, preset_name)
            settings: list[PropertyInfo] = []
            for i in range(cfg.size()):
                s = cfg.getSetting(i)
                device = s.getDeviceLabel()
                prop = s.getPropertyName()
                val = s.getPropertyValue()
                if enrich:
                    info = PropertyInfo.from_core(core, device, prop)
                    settings.append(dataclasses.replace(info, value=val))
                else:
                    settings.append(
                        PropertyInfo(name=prop, device_label=device, value=val)
                    )
            presets[preset_name] = ConfigPreset(
                name=preset_name, settings=settings
            )
        return cls(name=group_name, presets=presets)

    @classmethod
    def all_from_core(
        cls,
        core: Any,
        *,
        enrich: bool = False,
    ) -> tuple[ConfigGroup, ...]:
        """Read all configuration groups from core.

        If *enrich* is True, settings carry full property metadata.
        The ``is_channel_group`` flag is set automatically.
        """
        channel_group = ""
        with suppress(Exception):
            channel_group = core.getChannelGroup()

        groups: list[ConfigGroup] = []
        for name in core.getAvailableConfigGroups():
            group = cls.from_core(core, name, enrich=enrich)
            group.is_channel_group = name == channel_group
            groups.append(group)
        return tuple(groups)


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

    @classmethod
    def from_core(cls, core: Any, config_name: str) -> PixelSizePreset:
        """Read a single pixel size preset from core."""
        cfg = core.getPixelSizeConfigData(config_name)
        settings = [
            PropertySetting(
                device=(s := cfg.getSetting(i)).getDeviceLabel(),
                property=s.getPropertyName(),
                value=s.getPropertyValue(),
            )
            for i in range(cfg.size())
        ]

        affine = core.getPixelSizeAffineByID(config_name)

        dxdz = 0.0
        dydz = 0.0
        optimal_z_um = 0.0
        if hasattr(core, "getPixelSizedxdz"):
            dxdz = core.getPixelSizedxdz(config_name)
        if hasattr(core, "getPixelSizedydz"):
            dydz = core.getPixelSizedydz(config_name)
        if hasattr(core, "getPixelSizeOptimalZUm"):
            optimal_z_um = core.getPixelSizeOptimalZUm(config_name)

        return cls(
            name=config_name,
            settings=settings,
            pixel_size_um=core.getPixelSizeUmByID(config_name),
            affine=affine,
            dxdz=dxdz,
            dydz=dydz,
            optimal_z_um=optimal_z_um,
        )

    @classmethod
    def all_from_core(cls, core: Any) -> tuple[PixelSizePreset, ...]:
        """Read all pixel size presets from core."""
        return tuple(
            cls.from_core(core, name)
            for name in core.getAvailablePixelSizeConfigs()
        )

    def apply_to_core(self, core: Any) -> None:
        """Define this pixel size preset in core."""
        for s in self.settings:
            core.definePixelSizeConfig(
                self.name, s.device, s.property, s.value
            )
        core.setPixelSizeUm(self.name, self.pixel_size_um)
        core.setPixelSizeAffine(self.name, self.affine)


@dataclass(slots=True)
class SystemState:
    """Complete snapshot of a running system."""

    devices: tuple[DeviceInfo, ...] = ()
    config_groups: tuple[ConfigGroup, ...] = ()
    pixel_size_configs: tuple[PixelSizePreset, ...] = ()

    @classmethod
    def from_core(cls, core: Any, *, cached: bool = True) -> SystemState:
        """Read a complete snapshot of the running system."""
        return cls(
            devices=DeviceInfo.all_from_core(core, cached=cached),
            config_groups=ConfigGroup.all_from_core(core),
            pixel_size_configs=PixelSizePreset.all_from_core(core),
        )
