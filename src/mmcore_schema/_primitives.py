"""Shared primitives used by both config and state modules."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, fields
from typing import Any

AffineTuple = tuple[float, float, float, float, float, float]
IDENTITY_AFFINE: AffineTuple = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


@dataclass(slots=True)
class PropertySetting:
    """A single device property setting (device, property, value)."""

    device: str
    property: str
    value: str

    def __post_init__(self) -> None:
        self.value = str(self.value)

    def as_tuple(self) -> tuple[str, str, str]:
        """Return as a (device, property, value) tuple."""
        return self.device, self.property, self.value

    @classmethod
    def from_dict(cls, data: Any) -> PropertySetting:
        """Create from a dict, tuple/list, or existing instance."""
        if isinstance(data, cls):
            return data
        if isinstance(data, (list, tuple)):
            return cls(device=str(data[0]), property=str(data[1]), value=str(data[2]))
        return cls(
            device=data["device"],
            property=data["property"],
            value=str(data["value"]),
        )


# --------------- Serialization helpers ---------------


def dataclass_to_dict(
    obj: Any,
    *,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> dict[str, Any]:
    """Serialize a dataclass instance to a dictionary."""
    result: dict[str, Any] = {}
    for f in fields(obj):
        val = getattr(obj, f.name)
        if exclude_none and val is None:
            continue
        if exclude_defaults and _is_default(f, val):
            continue
        result[f.name] = _serialize_value(
            val, exclude_defaults=exclude_defaults, exclude_none=exclude_none
        )
    return result


def _is_default(f: dataclasses.Field[Any], val: Any) -> bool:
    """Check if a field value equals its default."""
    if f.default is not dataclasses.MISSING:
        return val == f.default
    if f.default_factory is not dataclasses.MISSING:  # type: ignore[arg-type]
        return val == f.default_factory()  # type: ignore[misc]
    return False


def _serialize_value(
    val: Any,
    *,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> Any:
    """Recursively serialize a value for dict output."""
    kw = {"exclude_defaults": exclude_defaults, "exclude_none": exclude_none}
    if dataclasses.is_dataclass(val) and not isinstance(val, type):
        return dataclass_to_dict(val, **kw)
    if isinstance(val, dict):
        return {k: _serialize_value(v, **kw) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_serialize_value(item, **kw) for item in val]
    return val
