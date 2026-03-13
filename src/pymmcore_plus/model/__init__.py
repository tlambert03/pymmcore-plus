from __future__ import annotations

import importlib
import warnings

__all__ = [
    "AvailableDevice",
    "ConfigGroup",
    "ConfigPreset",
    "CoreDevice",
    "Device",
    "Microscope",
    "PixelSizeGroup",
    "PixelSizePreset",
    "Property",
    "Setting",
]

_REPLACEMENTS: dict[str, str] = {
    "AvailableDevice": "mmcore_schema.state.DeviceInfo",
    "ConfigGroup": "mmcore_schema.state.ConfigGroup",
    "ConfigPreset": "mmcore_schema.state.ConfigPreset",
    "CoreDevice": "mmcore_schema.state.DeviceInfo",
    "Device": "mmcore_schema.state.DeviceInfo",
    "Microscope": "mmcore_schema.MMConfig + mmcore_schema.state.SystemState.from_core",
    "PixelSizeGroup": "mmcore_schema.state.PixelSizePreset.all_from_core",
    "PixelSizePreset": "mmcore_schema.state.PixelSizePreset",
    "Property": "mmcore_schema.state.PropertyInfo",
    "Setting": "mmcore_schema.PropertySetting",
}

_SOURCES: dict[str, tuple[str, str]] = {
    "AvailableDevice": ("._device", "AvailableDevice"),
    "ConfigGroup": ("._config_group", "ConfigGroup"),
    "ConfigPreset": ("._config_group", "ConfigPreset"),
    "CoreDevice": ("._core_device", "CoreDevice"),
    "Device": ("._device", "Device"),
    "Microscope": ("._microscope", "Microscope"),
    "PixelSizeGroup": ("._pixel_size_config", "PixelSizeGroup"),
    "PixelSizePreset": ("._pixel_size_config", "PixelSizePreset"),
    "Property": ("._property", "Property"),
    "Setting": ("._config_group", "Setting"),
}


def __getattr__(name: str) -> object:
    if name in _REPLACEMENTS:
        warnings.warn(
            f"Importing {name} from pymmcore_plus.model is deprecated and will "
            f"be removed in a future version. Use {_REPLACEMENTS[name]} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        module_path, attr_name = _SOURCES[name]
        mod = importlib.import_module(module_path, __package__)
        return getattr(mod, attr_name)
    raise AttributeError(f"module 'pymmcore_plus.model' has no attribute {name!r}")
