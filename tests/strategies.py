"""Reusable Hypothesis strategies for CMMCorePlus property testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypothesis import strategies as st

from pymmcore_plus.core._constants import PropertyType

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

    from pymmcore_plus import CMMCorePlus
    from pymmcore_plus.core._property import DeviceProperty


def writable_properties(core: CMMCorePlus) -> list[DeviceProperty]:
    """Return list of non-read-only, non-pre-init DeviceProperty objects."""
    return [
        prop
        for prop in core.iterProperties(is_read_only=False, as_object=True)
        if not prop.isPreInit()
    ]


def property_value_strategy(prop: DeviceProperty) -> SearchStrategy:
    """Generate valid values for a DeviceProperty based on its metadata."""
    allowed = prop.allowedValues()
    if allowed:
        return st.sampled_from(list(allowed))

    if prop.hasLimits():
        lo, hi = prop.range()
        ptype = prop.type()
        if ptype == PropertyType.Integer:
            return st.integers(int(lo), int(hi))
        if ptype == PropertyType.Float:
            return st.floats(lo, hi, allow_nan=False, allow_infinity=False)

    ptype = prop.type()
    pytype = ptype.to_python()
    if pytype is int:
        return st.integers(0, 1000)
    if pytype is float:
        return st.floats(0.0, 1000.0, allow_nan=False, allow_infinity=False)
    return st.text(min_size=1, max_size=20, alphabet=st.characters(codec="ascii"))


def out_of_range_value_strategy(prop: DeviceProperty) -> SearchStrategy | None:
    """Generate values outside declared limits, or None if no limits."""
    if not prop.hasLimits():
        return None

    lo, hi = prop.range()
    ptype = prop.type()
    if ptype == PropertyType.Integer:
        below = st.integers(int(lo) - 1000, int(lo) - 1)
        above = st.integers(int(hi) + 1, int(hi) + 1000)
        return st.one_of(below, above)
    if ptype == PropertyType.Float:
        below = st.floats(lo - 1000, lo - 0.01, allow_nan=False, allow_infinity=False)
        above = st.floats(hi + 0.01, hi + 1000, allow_nan=False, allow_infinity=False)
        return st.one_of(below, above)
    return None


def exposure_strategy() -> SearchStrategy[float]:
    """Strategy for exposure values (ms), rounded to 2 decimal places.

    DemoCamera truncates exposure to ~2 decimal places.
    """
    return st.floats(1.0, 1000.0, allow_nan=False, allow_infinity=False).map(
        lambda x: round(x, 2)
    )


def stage_position_strategy() -> SearchStrategy[float]:
    """Strategy for single-axis (Z) stage positions.

    DemoCamera Z stage has limited range (~±200).
    """
    return st.floats(-200.0, 200.0, allow_nan=False, allow_infinity=False)


def xy_position_strategy() -> SearchStrategy[tuple[float, float]]:
    """Strategy for XY stage positions.

    Uses integers mapped to floats to avoid slow float edge-case exploration.
    """
    s = st.integers(-1000, 1000).map(float)
    return st.tuples(s, s)


def state_index_strategy(core: CMMCorePlus, device: str) -> SearchStrategy[int]:
    """Strategy for valid state device indices."""
    n = core.getNumberOfStates(device)
    return st.integers(0, n - 1)


def state_label_strategy(core: CMMCorePlus, device: str) -> SearchStrategy[str]:
    """Strategy for valid state device labels."""
    labels = list(core.getStateLabels(device))
    return st.sampled_from(labels)


def roi_strategy() -> SearchStrategy[tuple[int, int, int, int]]:
    """Strategy for ROI tuples (x, y, w, h) within 512x512 DemoCamera bounds."""
    return st.tuples(
        st.integers(0, 256),
        st.integers(0, 256),
        st.integers(1, 256),
        st.integers(1, 256),
    ).filter(lambda t: t[0] + t[2] <= 512 and t[1] + t[3] <= 512)
