"""Standalone IntEnums for Micro-Manager device types.

These duplicate the enums from pymmcore/pymmcore-plus with identical int values,
allowing cross-package equality checks (e.g.
``mmcore_schema.DeviceType.Camera == pymmcore_plus.DeviceType.Camera`` is True).
"""

from __future__ import annotations

from enum import IntEnum


class DeviceType(IntEnum):
    """Micro-Manager device type identifiers."""

    Unknown = 0
    Any = 1
    Camera = 2
    Shutter = 3
    State = 4
    Stage = 5
    XYStage = 6
    Serial = 7
    Generic = 8
    AutoFocus = 9
    Core = 10
    ImageProcessor = 11
    SignalIO = 12
    Magnifier = 13
    SLM = 14
    Hub = 15
    Galvo = 16
    PressurePump = 17
    VolumetricPump = 18

    def __str__(self) -> str:
        return str(self.name)


class PropertyType(IntEnum):
    """Micro-Manager property type identifiers."""

    Undef = 0
    String = 1
    Float = 2
    Integer = 3

    def __repr__(self) -> str:
        _map = {0: "undefined", 1: "str", 2: "float", 3: "int"}
        return _map[self.value]


class FocusDirection(IntEnum):
    """Focus direction for stage devices."""

    Unknown = 0
    TowardSample = 1
    AwayFromSample = -1
