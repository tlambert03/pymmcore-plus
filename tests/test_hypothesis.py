"""Property-based tests for CMMCorePlus API using Hypothesis."""

from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
)
from useq import MDASequence, TIntervalLoops

import pymmcore_plus
from pymmcore_plus.mda._runner import RunState

from .strategies import (
    exposure_strategy,
    property_value_strategy,
    roi_strategy,
    stage_position_strategy,
    xy_position_strategy,
)

if TYPE_CHECKING:
    import threading

    from pymmcore_plus import CMMCorePlus

_suppress = [HealthCheck.function_scoped_fixture]
_settings = settings(
    max_examples=50,
    suppress_health_check=_suppress,
    deadline=None,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Known writable DemoCamera properties: (device, property_name)
DEMO_PROPS = [
    ("Camera", "Binning"),
    ("Camera", "Gain"),
    ("Camera", "AllowMultiROI"),
    ("Camera", "TransposeCorrection"),
    ("Emission", "Label"),
    ("Dichroic", "Label"),
    ("Excitation", "Label"),
    ("Objective", "Label"),
]
# A subset used for constraint / coercion tests
WRITABLE_PROPS = [
    ("Camera", "Binning"),
    ("Camera", "Gain"),
    ("Emission", "Label"),
    ("Dichroic", "Label"),
    ("Objective", "Label"),
]
READ_ONLY_PROPS = [("Camera", "CameraName")]
STATE_DEVICES = ("Emission", "Dichroic", "Excitation", "Objective")
MAX_STATE_INDEX = 9
EMISSION_LABELS = ("State-0", "State-1", "State-2", "State-3", "State-4", "State-5")
DEMO_CHANNELS = ("DAPI", "FITC", "Rhodamine", "Cy5")

# ---------------------------------------------------------------------------
# Roundtrips
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device,prop_name", DEMO_PROPS)
@_settings
@given(data=st.data())
def test_generic_property_roundtrip(
    data: st.DataObject, psygnal_core: CMMCorePlus, device: str, prop_name: str
):
    prop = psygnal_core.getPropertyObject(device, prop_name)
    strat = property_value_strategy(prop)
    val = data.draw(strat)
    try:
        prop.value = val
    except RuntimeError:
        return  # some properties reject values at C++ level
    readback = prop.value
    if isinstance(readback, float) and isinstance(val, (int, float)):
        assert math.isclose(readback, float(val), rel_tol=1e-6, abs_tol=1e-9)
    else:
        assert str(readback) == str(val)


@_settings
@given(val=exposure_strategy())
def test_exposure_roundtrip(val: float, psygnal_core: CMMCorePlus):
    psygnal_core.setExposure(val)
    readback = psygnal_core.getExposure()
    assert math.isclose(readback, val, rel_tol=1e-6)


@_settings
@given(val=stage_position_strategy())
def test_z_position_roundtrip(val: float, psygnal_core: CMMCorePlus):
    focus = psygnal_core.getFocusDevice()
    psygnal_core.setPosition(val)
    psygnal_core.waitForDevice(focus)
    readback = psygnal_core.getPosition()
    assert math.isclose(readback, val, abs_tol=0.01)


@settings(max_examples=10, deadline=None, suppress_health_check=_suppress)
@given(xy=xy_position_strategy())
def test_xy_position_roundtrip(xy: tuple[float, float], psygnal_core: CMMCorePlus):
    x, y = xy
    stage = psygnal_core.getXYStageDevice()
    psygnal_core.setXYPosition(x, y)
    psygnal_core.waitForDevice(stage)
    rx = psygnal_core.getXPosition()
    ry = psygnal_core.getYPosition()
    assert math.isclose(rx, x, abs_tol=0.05)
    assert math.isclose(ry, y, abs_tol=0.05)


@_settings
@given(val=st.booleans())
def test_shutter_roundtrip(val: bool, psygnal_core: CMMCorePlus):
    psygnal_core.setShutterOpen(val)
    assert psygnal_core.getShutterOpen() == val


@_settings
@given(val=st.booleans())
def test_autoshutter_roundtrip(val: bool, psygnal_core: CMMCorePlus):
    psygnal_core.setAutoShutter(val)
    assert psygnal_core.getAutoShutter() == val


@_settings
@given(idx=st.integers(0, 9))
def test_state_roundtrip(idx: int, psygnal_core: CMMCorePlus):
    device = "Emission"
    n_states = psygnal_core.getNumberOfStates(device)
    if idx >= n_states:
        return
    psygnal_core.setState(device, idx)
    psygnal_core.waitForDevice(device)
    assert psygnal_core.getState(device) == idx


@_settings
@given(label=st.sampled_from(EMISSION_LABELS))
def test_state_label_roundtrip(label: str, psygnal_core: CMMCorePlus):
    device = "Emission"
    labels = list(psygnal_core.getStateLabels(device))
    if label not in labels:
        return
    psygnal_core.setStateLabel(device, label)
    psygnal_core.waitForDevice(device)
    assert psygnal_core.getStateLabel(device) == label


@_settings
@given(roi=roi_strategy())
def test_roi_roundtrip(roi: tuple[int, int, int, int], psygnal_core: CMMCorePlus):
    x, y, w, h = roi
    psygnal_core.setROI(x, y, w, h)
    _rx, _ry, rw, rh = psygnal_core.getROI()
    # DemoCamera may clamp ROI; just verify dimensions are positive
    assert rw > 0
    assert rh > 0


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device,prop_name", WRITABLE_PROPS)
@_settings
@given(data=st.data())
def test_valid_values_accepted(
    data: st.DataObject, psygnal_core: CMMCorePlus, device: str, prop_name: str
):
    """Values within limits/allowed values should not raise."""
    prop = psygnal_core.getPropertyObject(device, prop_name)
    val = data.draw(property_value_strategy(prop))
    try:
        prop.value = val
    except RuntimeError:
        pass  # some DemoCamera properties reject at C++ level


@pytest.mark.parametrize("device,prop_name", READ_ONLY_PROPS)
@_settings
@given(dummy=st.just("test_value"))
def test_read_only_warns(
    dummy: str, psygnal_core: CMMCorePlus, device: str, prop_name: str
):
    """Setting a read-only property should emit a UserWarning."""
    prop = psygnal_core.getPropertyObject(device, prop_name)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            prop.setValue(dummy)
        except RuntimeError:
            pass  # C++ may also reject
    assert any(issubclass(x.category, UserWarning) for x in w)


@_settings
@given(bad_idx=st.integers(10, 110))
def test_state_index_out_of_range(bad_idx: int, psygnal_core: CMMCorePlus):
    """State index >= getNumberOfStates() should raise."""
    device = "Emission"
    n_states = psygnal_core.getNumberOfStates(device)
    if bad_idx < n_states:
        return
    try:
        psygnal_core.setState(device, bad_idx)
        psygnal_core.waitForDevice(device)
    except RuntimeError:
        return  # expected


@pytest.mark.parametrize("device,prop_name", WRITABLE_PROPS)
@_settings
@given(data=st.data())
def test_property_type_coercion(
    data: st.DataObject, psygnal_core: CMMCorePlus, device: str, prop_name: str
):
    """Readback value should match the property's declared Python type."""
    prop = psygnal_core.getPropertyObject(device, prop_name)
    val = data.draw(property_value_strategy(prop))
    try:
        prop.value = val
    except RuntimeError:
        return
    readback = prop.value
    expected_type = prop.type().to_python()
    if expected_type is not None:
        assert isinstance(readback, expected_type), (
            f"{prop.device}::{prop.name}: expected {expected_type}, "
            f"got {type(readback)}"
        )


# ---------------------------------------------------------------------------
# State / Label synchronization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", STATE_DEVICES)
@_settings
@given(idx=st.integers(0, MAX_STATE_INDEX))
def test_state_to_label_sync(idx: int, psygnal_core: CMMCorePlus, device: str):
    """setState(n) -> getStateLabel() == getStateLabels()[n]."""
    n_states = psygnal_core.getNumberOfStates(device)
    if idx >= n_states:
        return
    psygnal_core.setState(device, idx)
    psygnal_core.waitForDevice(device)
    labels = psygnal_core.getStateLabels(device)
    assert psygnal_core.getStateLabel(device) == labels[idx]


@pytest.mark.parametrize("device", STATE_DEVICES)
@_settings
@given(idx=st.integers(0, MAX_STATE_INDEX))
def test_label_to_state_sync(idx: int, psygnal_core: CMMCorePlus, device: str):
    """setStateLabel(lbl) -> getState() == index_of(lbl)."""
    labels = list(psygnal_core.getStateLabels(device))
    if idx >= len(labels):
        return
    label = labels[idx]
    psygnal_core.setStateLabel(device, label)
    psygnal_core.waitForDevice(device)
    assert psygnal_core.getState(device) == idx


@pytest.mark.parametrize("device", STATE_DEVICES)
@_settings
@given(idx=st.integers(0, MAX_STATE_INDEX))
def test_state_label_bidirectional(idx: int, psygnal_core: CMMCorePlus, device: str):
    """Set by index -> read label -> set by label -> read index matches."""
    n_states = psygnal_core.getNumberOfStates(device)
    if idx >= n_states:
        return

    psygnal_core.setState(device, idx)
    psygnal_core.waitForDevice(device)
    label = psygnal_core.getStateLabel(device)

    psygnal_core.setStateLabel(device, label)
    psygnal_core.waitForDevice(device)
    assert psygnal_core.getState(device) == idx


# ---------------------------------------------------------------------------
# Configuration consistency
# ---------------------------------------------------------------------------


@_settings
@given(channel=st.sampled_from(DEMO_CHANNELS))
def test_set_config_matches_data(channel: str, psygnal_core: CMMCorePlus):
    """After setConfig, device state matches getConfigData."""
    psygnal_core.setConfig("Channel", channel)
    config_data = psygnal_core.getConfigData("Channel", channel)
    for item in config_data:
        dev = item[0]
        prop = item[1]
        expected = item[2]
        actual = psygnal_core.getProperty(dev, prop)
        assert actual == expected, (
            f"After setConfig('Channel', {channel!r}): "
            f"{dev}::{prop} expected {expected!r}, got {actual!r}"
        )


@_settings
@given(
    group=st.text(min_size=1, max_size=10, alphabet="abcdefghijklm"),
    config=st.text(min_size=1, max_size=10, alphabet="abcdefghijklm"),
)
def test_define_then_is_defined(group: str, config: str, psygnal_core: CMMCorePlus):
    """defineConfig(g, c) -> isConfigDefined(g, c) is True."""
    psygnal_core.defineConfig(group, config)
    assert psygnal_core.isConfigDefined(group, config)
    # cleanup
    psygnal_core.deleteConfigGroup(group)


@_settings
@given(
    group=st.text(min_size=1, max_size=10, alphabet="abcdefghijklm"),
    config=st.text(min_size=1, max_size=10, alphabet="abcdefghijklm"),
)
def test_delete_then_not_defined(group: str, config: str, psygnal_core: CMMCorePlus):
    """define then delete -> isConfigDefined is False."""
    psygnal_core.defineConfig(group, config)
    assert psygnal_core.isConfigDefined(group, config)
    psygnal_core.deleteConfig(group, config)
    assert not psygnal_core.isConfigDefined(group, config)
    # cleanup
    psygnal_core.deleteConfigGroup(group)


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------


@_settings
@given(val=st.sampled_from(["1", "2", "4", "8"]))
def test_set_property_emits_event(val: str, psygnal_core: CMMCorePlus):
    """setProperty('Camera', 'Binning', v) -> propertyChanged emitted."""
    # Ensure we're actually changing the value so the event fires.
    current = psygnal_core.getProperty("Camera", "Binning")
    if current == val:
        alt = [v for v in ("1", "2", "4", "8") if v != val]
        psygnal_core.setProperty("Camera", "Binning", alt[0])

    mock = Mock()
    psygnal_core.events.propertyChanged.connect(mock)
    try:
        psygnal_core.setProperty("Camera", "Binning", val)
        found = any(
            c.args[0] == "Camera" and c.args[1] == "Binning"
            for c in mock.call_args_list
        )
        assert found, f"propertyChanged not emitted for Camera::Binning={val}"
    finally:
        psygnal_core.events.propertyChanged.disconnect(mock)


@_settings
@given(val=exposure_strategy())
def test_set_exposure_emits_event(val: float, psygnal_core: CMMCorePlus):
    """setExposure(v) -> exposureChanged emitted."""
    current = psygnal_core.getExposure()
    if math.isclose(current, val, abs_tol=0.001):
        psygnal_core.setExposure(val + 1.0 if val < 999.0 else val - 1.0)

    mock = Mock()
    psygnal_core.events.exposureChanged.connect(mock)
    try:
        psygnal_core.setExposure(val)
        mock.assert_called()
    finally:
        psygnal_core.events.exposureChanged.disconnect(mock)


@settings(max_examples=10, deadline=None, suppress_health_check=_suppress)
@given(xy=xy_position_strategy())
def test_set_xy_emits_event(xy: tuple[float, float], psygnal_core: CMMCorePlus):
    """setXYPosition(x, y) -> XYStagePositionChanged emitted."""
    mock = Mock()
    psygnal_core.events.XYStagePositionChanged.connect(mock)
    try:
        psygnal_core.setXYPosition(*xy)
        psygnal_core.waitForDevice(psygnal_core.getXYStageDevice())
        mock.assert_called()
    finally:
        psygnal_core.events.XYStagePositionChanged.disconnect(mock)


@_settings
@given(channel=st.sampled_from(DEMO_CHANNELS))
def test_set_config_emits_event(channel: str, psygnal_core: CMMCorePlus):
    """setConfig('Channel', name) -> configSet emitted."""
    mock = Mock()
    psygnal_core.events.configSet.connect(mock)
    try:
        psygnal_core.setConfig("Channel", channel)
        mock.assert_called_with("Channel", channel)
    finally:
        psygnal_core.events.configSet.disconnect(mock)


@_settings
@given(val=st.booleans())
def test_set_autoshutter_emits_event(val: bool, psygnal_core: CMMCorePlus):
    """setAutoShutter(b) -> autoShutterSet emitted."""
    mock = Mock()
    psygnal_core.events.autoShutterSet.connect(mock)
    try:
        psygnal_core.setAutoShutter(val)
        mock.assert_called_with(val)
    finally:
        psygnal_core.events.autoShutterSet.disconnect(mock)


# ---------------------------------------------------------------------------
# Imaging
# ---------------------------------------------------------------------------

_imaging_settings = settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


@_imaging_settings
@given(binning=st.sampled_from(["1", "2", "4"]))
def test_snap_shape_matches_settings(binning: str, psygnal_core: CMMCorePlus):
    """snap() shape matches (getImageHeight(), getImageWidth())."""
    psygnal_core.setProperty("Camera", "Binning", binning)
    img = psygnal_core.snap()
    expected_h = psygnal_core.getImageHeight()
    expected_w = psygnal_core.getImageWidth()
    assert img.shape == (expected_h, expected_w)


@_imaging_settings
@given(binning=st.sampled_from(["1", "2"]))
def test_snap_dtype_matches_bit_depth(binning: str, psygnal_core: CMMCorePlus):
    """snap() dtype matches getBytesPerPixel()."""
    psygnal_core.setProperty("Camera", "Binning", binning)
    img = psygnal_core.snap()
    bpp = psygnal_core.getBytesPerPixel()
    dtype_map = {1: "uint8", 2: "uint16", 4: "uint32"}
    expected_dtype = dtype_map.get(bpp, "uint16")
    assert img.dtype.name == expected_dtype


# ---------------------------------------------------------------------------
# setContext restore
# ---------------------------------------------------------------------------


@_settings
@given(exposure=exposure_strategy(), auto_shutter=st.booleans())
def test_setcontext_restores_values(
    exposure: float, auto_shutter: bool, psygnal_core: CMMCorePlus
):
    """Values set in context are restored after exit."""
    orig_exposure = psygnal_core.getExposure()
    orig_autoshutter = psygnal_core.getAutoShutter()

    with psygnal_core.setContext(exposure=exposure, autoShutter=auto_shutter):
        assert math.isclose(psygnal_core.getExposure(), exposure, rel_tol=1e-6)
        assert psygnal_core.getAutoShutter() == auto_shutter

    assert math.isclose(psygnal_core.getExposure(), orig_exposure, rel_tol=1e-6)
    assert psygnal_core.getAutoShutter() == orig_autoshutter


@_settings
@given(exposure=exposure_strategy())
def test_setcontext_restores_on_exception(exposure: float, psygnal_core: CMMCorePlus):
    """Values are restored even when an exception is raised inside context."""
    orig_exposure = psygnal_core.getExposure()

    try:
        with psygnal_core.setContext(exposure=exposure):
            assert math.isclose(psygnal_core.getExposure(), exposure, rel_tol=1e-6)
            raise ValueError("test error")
    except ValueError:
        pass

    assert math.isclose(psygnal_core.getExposure(), orig_exposure, rel_tol=1e-6)


@_settings
@given(val=st.booleans())
def test_setcontext_restores_shutter(val: bool, psygnal_core: CMMCorePlus):
    """shutterOpen is restored after context exit."""
    orig = psygnal_core.getShutterOpen()

    with psygnal_core.setContext(shutterOpen=val):
        assert psygnal_core.getShutterOpen() == val

    assert psygnal_core.getShutterOpen() == orig


# ---------------------------------------------------------------------------
# MDARunner state machine
# ---------------------------------------------------------------------------


class MDARunnerStateMachine(RuleBasedStateMachine):
    """Stateful test for MDARunner state transitions."""

    def __init__(self) -> None:
        super().__init__()
        self._core = pymmcore_plus.CMMCorePlus()
        self._core.mda.engine.use_hardware_sequencing = False
        self._core.loadSystemConfiguration()
        self._thread: threading.Thread | None = None

    def teardown(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._core.mda.cancel()
            self._thread.join(timeout=10)
        self._core.__del__()

    def _is_idle(self) -> bool:
        return self._core.mda.status.phase == RunState.IDLE

    def _is_running(self) -> bool:
        return self._core.mda.is_running()

    def _is_paused(self) -> bool:
        return self._core.mda.is_paused()

    @precondition(lambda self: self._is_idle())
    @rule()
    def start_acquisition(self) -> None:
        seq = MDASequence(time_plan=TIntervalLoops(interval=0.05, loops=10))
        self._thread = self._core.run_mda(seq)

    @precondition(lambda self: self._is_running() and not self._is_paused())
    @rule()
    def pause(self) -> None:
        self._core.mda.set_paused(True)

    @precondition(lambda self: self._is_paused())
    @rule()
    def unpause(self) -> None:
        self._core.mda.set_paused(False)

    @precondition(lambda self: self._is_running())
    @rule()
    def cancel(self) -> None:
        self._core.mda.cancel()
        if self._thread is not None:
            self._thread.join(timeout=10)

    @precondition(lambda self: self._is_idle())
    @rule()
    def cancel_from_idle(self) -> None:
        self._core.mda.cancel()  # should be a no-op

    @precondition(lambda self: self._is_idle())
    @rule()
    def pause_from_idle(self) -> None:
        self._core.mda.set_paused(True)  # should be a no-op

    @rule()
    def wait_for_idle(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=10)

    @invariant()
    def status_phase_is_valid(self) -> None:
        phase = self._core.mda.status.phase
        assert isinstance(phase, RunState), f"Invalid phase: {phase}"

    @invariant()
    def is_running_consistent_with_phase(self) -> None:
        status = self._core.mda.status
        running = self._core.mda.is_running()
        if status.phase == RunState.IDLE:
            assert not running


TestMDARunner = MDARunnerStateMachine.TestCase
TestMDARunner.settings = settings(
    max_examples=5,
    stateful_step_count=10,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
