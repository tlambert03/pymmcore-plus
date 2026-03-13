"""Schema for Micro-Manager configuration and state."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pymmcore-plus")
except PackageNotFoundError:
    __version__ = "uninstalled"

from ._primitives import IDENTITY_AFFINE, AffineTuple, PropertySetting
from .conversion import convert_file
from .enums import DeviceType, FocusDirection, PropertyType
from .mmconfig import (
    SCHEMA_URL_BASE,
    ConfigGroup,
    Configuration,
    Device,
    MMConfig,
    PixelSizeConfiguration,
    PropertyValue,
)

__all__ = [
    "IDENTITY_AFFINE",
    "SCHEMA_URL_BASE",
    "AffineTuple",
    "ConfigGroup",
    "Configuration",
    "Device",
    "DeviceType",
    "FocusDirection",
    "MMConfig",
    "PixelSizeConfiguration",
    "PropertySetting",
    "PropertyType",
    "PropertyValue",
    "__version__",
    "convert_file",
]
