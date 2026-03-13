"""Standalone functions for reading/writing state between CMMCore and mmcore_schema.

These functions return mmcore_schema.state dataclass instances, replacing the
CoreObject protocol pattern in pymmcore_plus.model.
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from mmcore_schema import DeviceType, FocusDirection, PropertySetting, PropertyType
from mmcore_schema.state import (
    ConfigGroup,
    ConfigPreset,
    DeviceInfo,
    PixelSizePreset,
    PropertyInfo,
    SystemState,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    import pymmcore

# --------------- Property / Device reads ---------------


def read_property_info(
    core: pymmcore.CMMCore,
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

    return PropertyInfo(
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


def read_properties(
    core: pymmcore.CMMCore,
    device: str,
    *,
    cached: bool = True,
    device_type: DeviceType | None = None,
) -> tuple[PropertyInfo, ...]:
    """Read all properties for a device."""
    if device_type is None:
        device_type = DeviceType(int(core.getDeviceType(device)))
    return tuple(
        read_property_info(
            core, device, prop, cached=cached, device_type=device_type
        )
        for prop in core.getDevicePropertyNames(device)
    )


def read_device_info(
    core: pymmcore.CMMCore,
    label: str,
    *,
    cached: bool = True,
) -> DeviceInfo:
    """Read runtime information about a loaded device."""
    devtype_raw = core.getDeviceType(label)
    devtype = DeviceType(int(devtype_raw))

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
                focus_direction = FocusDirection(int(core.getFocusDirection(label)))

    return DeviceInfo(
        label=label,
        library=core.getDeviceLibrary(label),
        name=core.getDeviceName(label),
        description=core.getDeviceDescription(label),
        type=devtype,
        properties=read_properties(core, label, cached=cached, device_type=devtype),
        parent_label=core.getParentLabel(label),
        state_labels=state_labels,
        focus_direction=focus_direction,
        child_names=child_names,
    )


def read_devices(
    core: pymmcore.CMMCore,
    *,
    cached: bool = True,
) -> tuple[DeviceInfo, ...]:
    """Read information about all loaded devices."""
    return tuple(
        read_device_info(core, lbl, cached=cached) for lbl in core.getLoadedDevices()
    )


# --------------- Config group reads ---------------


def read_config_group(
    core: pymmcore.CMMCore,
    group_name: str,
) -> ConfigGroup:
    """Read a single config group with all its presets from core."""
    presets: dict[str, ConfigPreset] = {}
    for preset_name in core.getAvailableConfigs(group_name):
        cfg = core.getConfigData(group_name, preset_name)
        settings = [
            PropertySetting(
                device=(s := cfg.getSetting(i)).getDeviceLabel(),
                property=s.getPropertyName(),
                value=s.getPropertyValue(),
            )
            for i in range(cfg.size())
        ]
        presets[preset_name] = ConfigPreset(name=preset_name, settings=settings)
    return ConfigGroup(name=group_name, presets=presets)


def read_config_groups(core: pymmcore.CMMCore) -> tuple[ConfigGroup, ...]:
    """Read all configuration groups from core."""
    return tuple(
        read_config_group(core, name) for name in core.getAvailableConfigGroups()
    )


# --------------- Pixel size reads ---------------


def read_pixel_size_preset(
    core: pymmcore.CMMCore,
    config_name: str,
) -> PixelSizePreset:
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

    return PixelSizePreset(
        name=config_name,
        settings=settings,
        pixel_size_um=core.getPixelSizeUmByID(config_name),
        affine=affine,
        dxdz=dxdz,
        dydz=dydz,
        optimal_z_um=optimal_z_um,
    )


def read_pixel_size_presets(core: pymmcore.CMMCore) -> tuple[PixelSizePreset, ...]:
    """Read all pixel size presets from core."""
    return tuple(
        read_pixel_size_preset(core, name)
        for name in core.getAvailablePixelSizeConfigs()
    )


# --------------- Composite reads ---------------


def read_system_state(
    core: pymmcore.CMMCore,
    *,
    cached: bool = True,
) -> SystemState:
    """Read a complete snapshot of the running system.

    Returns a SystemState containing all devices, config groups,
    and pixel size configurations.
    """
    return SystemState(
        devices=read_devices(core, cached=cached),
        config_groups=read_config_groups(core),
        pixel_size_configs=read_pixel_size_presets(core),
    )


# --------------- Apply functions ---------------


def apply_config(
    core: pymmcore.CMMCore,
    group_name: str,
    preset_name: str,
) -> None:
    """Apply a configuration preset to core."""
    core.setConfig(group_name, preset_name)
    core.waitForConfig(group_name, preset_name)


def apply_pixel_size_preset(
    core: pymmcore.CMMCore,
    preset: PixelSizePreset,
) -> None:
    """Define a single pixel size preset in core."""
    for s in preset.settings:
        core.definePixelSizeConfig(preset.name, s.device, s.property, s.value)
    core.setPixelSizeUm(preset.name, preset.pixel_size_um)
    core.setPixelSizeAffine(preset.name, preset.affine)


def apply_pixel_size_presets(
    core: pymmcore.CMMCore,
    presets: Iterable[PixelSizePreset],
) -> None:
    """Define multiple pixel size presets in core."""
    for preset in presets:
        apply_pixel_size_preset(core, preset)
