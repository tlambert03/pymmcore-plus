# UniMMCore

!!! tip "Experimental"

    This is an experimental feature, and the API may change in future releases.

## A unified controller of C++ and pure-Python devices

The [`UniMMCore`][pymmcore_plus.experimental.unicore.UniMMCore] class is a
subclass of [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] that can control both
"classic" C++ devices (via the CMMCore) as well as pure-Python device adapters.
This simplifies the task of controlling new devices using pure-Python code,
without the need to write and compile a C++ device adapter.

The Python devices work alongside the existing C++ device adapters, and you use
them through the same `CMMCorePlus` API.  When you call methods like
`core.setXYPosition()` or `core.snapImage()`, UniMMCore routes the call to the
appropriate device implementation (C++ or Python) based on which device is
currently active.  Properties and hardware sequencing are supported for Python
devices too.

## Getting started

To use UniMMCore, replace `CMMCorePlus` with `UniMMCore`:

```python
from pymmcore_plus.experimental.unicore import UniMMCore

# Instead of: core = CMMCorePlus()
core = UniMMCore()

# Load traditional C++ devices defined in a config file (optional)
core.loadSystemConfiguration(...)

# Load Python devices (we'll discuss creating these below)
from my_custom_devices import MyCamera

core.loadPyDevice("MyCamera", MyCamera())
core.initializeDevice("MyCamera")

# Set as the current camera device
core.setCameraDevice("MyCamera")

# Use the same API, UniMMCore routes to Python device automatically
core.setExposure(100)
img = core.snap()  # or core.snapImage(), followed by core.getImage()
```

## Supported device types

UniMMCore currently supports the following device types for Python
implementation (all of them share the [common methods](#common-methods)):

- [`CameraDevice`](#camera-devices-cameradevice) (and `SimpleCameraDevice`)
- [`StageDevice`](#stage-devices-stagedevice) (single axis, e.g. focus)
- [`XYStageDevice`](#xy-stage-devices-xystagedevice) (and `XYStepperStageDevice`)
- [`StateDevice`](#state-devices-statedevice)
- [`ShutterDevice`](#shutter-devices-shutterdevice)
- [`SLMDevice`](#slm-devices-slmdevice)
- [`HubDevice`](#hub-devices-hubdevice)
- [`GenericDevice`](#generic-devices-genericdevice)

### Common methods

All device base classes inherit from
[`Device`][pymmcore_plus.experimental.unicore.Device], and may re-implement any
of the following methods:

```python
from pymmcore_plus.experimental.unicore import Device


class MyDevice(Device):
    def initialize(self) -> None:
        """Initialize the device.

        Note: Communication with and initialization of the device should be
        done here, *not* in `__init__`.
        """

    def shutdown(self) -> None:
        """Called when device is unloaded."""

    def busy(self) -> bool:
        """Return `True` if the device is busy. (Returns False by default)."""

    @classmethod
    def name(cls) -> str:
        """Return the name of the device.

        By default, the class name is used.  (This is *not* the same as
        the user-defined label)
        """

    def description(self) -> str:
        """Return a description of the device.

        By default, the class docstring is used.
        """
```

### Camera devices (`CameraDevice`)

For image acquisition devices. Implement the following abstract methods:

```python
from collections.abc import Callable, Iterator, Sequence

import numpy as np

from pymmcore_plus.experimental.unicore import CameraDevice


class MyCamera(CameraDevice):
    def get_exposure(self) -> float:
        """Return current exposure time in milliseconds."""
        pass

    def set_exposure(self, exposure: float) -> None:
        """Set exposure time in milliseconds."""
        pass

    def shape(self) -> tuple[int, ...]:
        """Return (height, width, [channels]) of current image."""
        pass

    def dtype(self) -> np.dtype:
        """Return NumPy dtype of camera images."""
        pass

    def start_sequence(
        self, n: int | None, get_buffer: Callable[[Sequence[int], np.dtype], np.ndarray]
    ) -> Iterator[dict]:
        """Acquire `n` images (or until stopped, if `n` is None).

        For each image, call `get_buffer(shape, dtype)`, fill the returned array
        in place, and then yield a metadata dict for that image.
        """
        pass
```

`start_sequence` is used for sequence acquisitions *and* for `snapImage` (which
is a sequence of one), so it's the only acquisition method you need to write.

For simple or simulated cameras, you can use `SimpleCameraDevice` instead.  In
place of `shape()` and `start_sequence()`, it only needs `sensor_shape()` and
`snap()`, and it provides software ROI for you:

```python
import numpy as np

from pymmcore_plus.experimental.unicore import SimpleCameraDevice


class MySimpleCamera(SimpleCameraDevice):
    def get_exposure(self) -> float: ...
    def set_exposure(self, exposure: float) -> None: ...

    def sensor_shape(self) -> tuple[int, ...]:
        """Return (height, width) of the full sensor."""
        ...

    def dtype(self) -> np.dtype: ...

    def snap(self, buffer: np.ndarray) -> dict:
        """Fill the full-frame buffer with image data."""
        ...
```

!!! warning

    `SimpleCameraDevice` is *not* recommended for real hardware cameras: a
    per-frame `snap()` prevents SDK-level optimizations like ring buffers and DMA
    transfers. Use `CameraDevice` with `start_sequence()` instead.

### Stage devices (`StageDevice`)

For single-axis stages, like a focus drive (set it as the focus device with
`core.setFocusDevice(label)`):

```python
from pymmcore_plus.experimental.unicore import StageDevice


class MyZStage(StageDevice):
    def set_position_um(self, val: float) -> None:
        """Set stage position in micrometers."""

    def get_position_um(self) -> float:
        """Get current stage position in micrometers."""

    def set_origin(self) -> None:
        """Set the current position as the origin."""

    def home(self) -> None:
        """Move stage to home position."""

    def stop(self) -> None:
        """Stop stage movement."""
```

!!! note

    If you plan to save your configuration to a file (see
    [Python devices in config files](#python-devices-in-config-files)), also
    implement `set_focus_direction(self, sign: int)` (it may do nothing).  The
    saved file includes a `FocusDirection` line for each stage, and the default
    implementation raises an error when that line is loaded again.

### XY stage devices (`XYStageDevice`)

For controlling 2-axis positioning stages:

=== "Position motors"

    ```python
    from pymmcore_plus.experimental.unicore import XYStageDevice


    class MyStage(XYStageDevice):
        def set_position_um(self, x: float, y: float) -> None:
            """Set stage position in micrometers."""
            pass

        def get_position_um(self) -> tuple[float, float]:
            """Get current stage position in micrometers."""
            pass

        def set_origin_x(self) -> None:
            """Set current X position as origin."""
            pass

        def set_origin_y(self) -> None:
            """Set current Y position as origin."""
            pass

        def stop(self) -> None:
            """Stop stage movement."""
            pass

        def home(self) -> None:
            """Move stage to home position."""
            pass
    ```

=== "Stepper motor"

    For stepper motor stages with sequence support, use `XYStepperStageDevice`:

    ```python
    from pymmcore_plus.experimental.unicore import XYStepperStageDevice


    class MyStepperStage(XYStepperStageDevice):
        def get_position_steps(self) -> tuple[int, int]:
            """Get position in motor steps."""
            pass

        def set_position_steps(self, x: int, y: int) -> None:
            """Set position in motor steps."""
            pass

        def get_step_size_x_um(self) -> float:
            """Get X-axis step size in micrometers."""
            pass

        def get_step_size_y_um(self) -> float:
            """Get Y-axis step size in micrometers."""
            pass

        def home(self) -> None:
            """Move stage to home position."""
            pass

        def stop(self) -> None:
            """Stop stage movement."""
            pass

        # Additional methods for sequence support
        def get_sequence_max_length(self) -> int:
            """Maximum length of position sequences."""
            pass

        def send_sequence(self, sequence: tuple[tuple[float, float], ...]) -> None:
            """Load sequence of (x, y) positions."""
            pass
    ```

### State devices (`StateDevice`)

For devices with discrete states (filter wheels, objective turrets, etc.):

```python
from pymmcore_plus.experimental.unicore import StateDevice


class MyFilterWheel(StateDevice):
    def set_state(self, pos: int) -> None:
        """Set device to specified state/position."""
        pass

    def get_state(self) -> int:
        """Get current state/position."""
        pass
```

### Shutter devices (`ShutterDevice`)

For controlling shutters or any binary open/close devices:

```python
from pymmcore_plus.experimental.unicore import ShutterDevice


class MyShutter(ShutterDevice):
    def get_open(self) -> bool:
        """Return True if shutter is open."""
        pass

    def set_open(self, open: bool) -> None:
        """Open (True) or close (False) the shutter."""
        pass
```

### SLM devices (`SLMDevice`)

For Spatial Light Modulators:

```python
import numpy as np

from pymmcore_plus.experimental.unicore import SLMDevice


class MySLM(SLMDevice):
    def shape(self) -> tuple[int, ...]:
        """Return (height, width) of the SLM, or (height, width, 3) for RGB."""
        pass

    def dtype(self) -> np.dtype:
        """Return NumPy dtype of the SLM image (e.g. uint8)."""
        pass

    def set_image(self, pixels: np.ndarray) -> None:
        """Load an image into the SLM (without displaying it yet)."""
        pass

    def display_image(self) -> None:
        """Display the currently loaded image."""
        pass

    def get_exposure(self) -> float:
        """Get exposure time in milliseconds."""
        pass

    def set_exposure(self, interval_ms: float) -> None:
        """Set exposure time in milliseconds."""
        pass
```

The core derives `getSLMWidth`, `getSLMHeight`, `getSLMNumberOfComponents` and
`getSLMBytesPerPixel` from `shape()` and `dtype()`.  To support SLM sequences,
also override `get_sequence_max_length`, `send_sequence`, `start_sequence` and
`stop_sequence`.

### Hub devices (`HubDevice`)

For a controller that has other devices attached to it.  Override
`get_installed_peripherals()` to return `(name, description)` pairs, where each
`name` is the name of a device class importable from the same module as the hub:

```python
from pymmcore_plus.experimental.unicore import HubDevice


class MyHub(HubDevice):
    def get_installed_peripherals(self) -> list[tuple[str, str]]:
        return [("MyZStage", "Focus drive"), ("MyShutter", "Shutter")]
```

### Generic devices (`GenericDevice`)

For devices that don't fit other categories but need property control:

```python
from pymmcore_plus.experimental.unicore import GenericDevice


class MyGenericDevice(GenericDevice):
    # Only basic Device methods needed - mainly for property-only devices
    pass
```

## Device properties

Properties are defined either on the class using the
[`@pymm_property`][pymmcore_plus.experimental.unicore.pymm_property] decorator,
or dynamically at runtime using
[`Device.register_property`][pymmcore_plus.experimental.unicore.Device.register_property].

These two methods may be freely mixed, and accept largely the same arguments.

=== "`@pymm_property`"

    ```python
    from pymmcore_plus.experimental.unicore import GenericDevice, pymm_property


    class MyDevice(GenericDevice):
        _my_prop = 42

        @pymm_property(name="MyProp", default_value=42, limits=(0, 100))
        def my_prop(self) -> int:
            """MyProp property with limits 0-100 and default 42."""
            return self._my_prop

        @my_prop.setter
        def my_prop(self, value: int) -> None:
            self._my_prop = value
    ```

=== "`register_property`"

    In many cases, you may not know ahead of device initialization which
    properties are supported. In this case, you can register properties
    at runtime in `initialize()`:

    ```python
    from pymmcore_plus.experimental.unicore import GenericDevice


    class MyDevice(GenericDevice):
        def initialize(self) -> None:
            cls = type(self)
            self.register_property(
                name="MyProp",
                getter=cls._get_my_prop,
                setter=cls._set_my_prop,
                default_value=42,
                limits=(0, 100),
            )

        def _set_my_prop(self, value: int) -> None: ...

        def _get_my_prop(self) -> int: ...
    ```

### Properties with constraints

Properties may have value constraints such as numerical limits or
(categorical) allowed values:

```python
class MyStage(XYStageDevice):
    @pymm_property(limits=(0.0, 100.0))
    def speed(self) -> float:
        """Stage speed (0-100%)."""
        return self._speed
    
    @pymm_property(allowed_values=[1, 2, 4, 8])
    def step_size(self) -> int:
        """Step size multiplier."""
        return self._step_size
```

### Sequenceable properties

In order to declare a property as "sequenceable" (i.e. supporting hardware-synchronized
parameter changes), you must:

1. Define a `sequence_max_length` of greater than zero.
2. Implement `sequence_loader` and `sequence_starter`, (and optionally `sequence_stopper`)
   methods.

=== "`@pymm_property`"

    ```python
    class MyDevice(GenericDevice):
        @pymm_property(sequence_max_length=100)
        def someprop(self) -> float:
            return self._someprop

        @someprop.setter
        def set_someprop(self, value: float) -> None:
            self._someprop = value

        @someprop.sequence_loader
        def load_someprop_sequence(self, sequence: list[float]) -> None:
            """Load a sequence of someprop values into hardware."""

        @someprop.sequence_starter
        def start_someprop_sequence(self) -> None:
            """Tell hardware to start the sequence."""

        @someprop.sequence_stopper  # optional
        def stop_someprop_sequence(self) -> None:
            """Tell hardware to stop the sequence."""
    ```

=== "`register_property`"

    ```python
    class MyDevice(GenericDevice):
        def initialize(self) -> None:
            cls = type(self)
            self.register_property(
                name="someprop",
                getter=cls._get_someprop,
                setter=cls._set_someprop,
                sequence_loader=cls.load_someprop_sequence,
                sequence_starter=cls.start_someprop_sequence,
                sequence_stopper=cls.stop_someprop_sequence,
                sequence_max_length=100,
                default_value=10.0,
                limits=(0.1, 10000.0),
            )
        
        def _get_someprop(self) -> float:
            return self._someprop
        
        def _set_someprop(self, value: float) -> None:
            self._someprop = value
        
        def load_someprop_sequence(self, sequence: list[float]) -> None:
            """Load a sequence of someprop values into hardware."""
        
        def start_someprop_sequence(self) -> None:
            """Tell hardware to start the sequence."""
        
        def stop_someprop_sequence(self) -> None:
            """Tell hardware to stop the sequence."""
    ```

### Property types and validation

Properties are automatically typed based on their return annotations,
but you can be explicit:

```python
class MyDevice(GenericDevice):
    @pymm_property(property_type=str)
    def serial_number(self) -> str:
        return "12345"
    
    @pymm_property(property_type=int, limits=(1, 1000))
    def gain(self) -> int:
        return self._gain
```

## Device lifecycle

All Python devices follow this lifecycle:

### 1. Creation and loading

```python
# Create device instance
device = MyCamera()

# Load into core with a label
core.loadPyDevice("Camera1", device)
```

### 2. Initialization

```python
# Initialize the device (calls device.initialize())
core.initializeDevice("Camera1")
```

Override `initialize()` for device-specific setup:

```python
class MyCamera(CameraDevice):
    def initialize(self) -> None:
        """Called when device is initialized."""
        # Setup hardware connections, configure device, etc.
        self.connect_to_hardware()
        super().initialize()  # Call parent if needed
```

### 3. Usage

Once loaded and initialized, use the device through the standard CMMCore API:

```python
# Set as current device
core.setCameraDevice("Camera1")

# Use standard API
core.setExposure(50)
image = core.snap()
```

### 4. Shutdown

```python
# Shutdown specific device
core.unloadDevice("Camera1")

# Or shutdown all devices
core.unloadAllDevices()
```

Override `shutdown()` for cleanup:

```python
class MyCamera(CameraDevice):
    def shutdown(self) -> None:
        """Called when device is unloaded."""
        self.disconnect_from_hardware()
        super().shutdown()
```

## Thread safety

When the core calls into a Python device, it does so with the device locked, so
those calls don't run concurrently.

If you need manual locking:

```python
device = MyCamera()
core.loadPyDevice("Camera", device)

# Manual locking
with device:
    # Device is locked for this block
    device.some_internal_method()
```

## Events and metadata

You can connect to the [events](events.md) of a `UniMMCore` as usual, but note
that it doesn't (yet) emit `propertyChanged` when you set a property on a Python
device, or `exposureChanged` for a Python camera (state devices are the
exception).  Until it does, a device can emit events itself, through its `core`
attribute:

```python
class MyDevice(GenericDevice):
    _level = 1

    @pymm_property(limits=(0, 10))
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, value: int) -> None:
        self._level = value
        self.core.events.propertyChanged.emit(self.get_label(), "level", str(value))
```

(Please open an issue if this matters for your device.)

Sequence acquisitions include metadata just as C++ camera adapters do:

```python
core.startSequenceAcquisition(10, 0, True)
while core.isSequenceRunning() or core.getRemainingImageCount():
    if core.getRemainingImageCount():
        img, metadata = core.popNextImageAndMD()
        print(f"Image {metadata['ImageNumber']}: {metadata['ElapsedTime-ms']} ms")
```

(The metadata contains the standard keys, like `ImageNumber`, `ElapsedTime-ms`,
`Camera`, `Width` and `Height`, plus whatever your `start_sequence` yielded.)

## Error handling

Exceptions raised in Python devices propagate to the caller:

```python
class MyCamera(CameraDevice):
    def set_exposure(self, exposure: float) -> None:
        if exposure < 0:
            raise ValueError("Exposure must be positive")
        if exposure > 10000:
            raise ValueError("Exposure too long")
        self._exposure = exposure
```

```python
core.setExposure(-5)  # raises ValueError: Exposure must be positive
```

## Python devices in config files

`UniMMCore` can load and save Python devices in regular Micro-Manager `.cfg`
files.  Python device lines are prefixed with `#py `, so a regular
`CMMCorePlus` (or Micro-Manager itself) reads them as comments and ignores them:

```text
# C++ devices
Device,Camera,DemoCamera,DCam

# Python devices: pyDevice,<label>,<module>,<class>
#py pyDevice,PyCamera,my_devices,MyCamera
#py Property,Core,Camera,PyCamera
```

The module must be importable (e.g. installed, or on `sys.path`) when the file
is loaded with `core.loadSystemConfiguration("my.cfg")`.  To write the current
state (C++ and Python devices) to a file, use
`core.saveSystemConfiguration("my.cfg")`.  Pass `prefix_py_devices=False` to
write the Python lines without the `#py ` prefix (the file can then only be
loaded by `UniMMCore`).

## Complete examples

For complete working examples, see these scripts in the
[`examples/`](https://github.com/pymmcore-plus/pymmcore-plus/tree/main/examples)
folder of the repository:

- [`unicore_camera.py`](https://github.com/pymmcore-plus/pymmcore-plus/blob/main/examples/unicore_camera.py):
  a synthetic camera with temporal patterns
- [`unicore_hamamatsu.py`](https://github.com/pymmcore-plus/pymmcore-plus/blob/main/examples/unicore_hamamatsu.py):
  a real Hamamatsu camera
- [`unicore.py`](https://github.com/pymmcore-plus/pymmcore-plus/blob/main/examples/unicore.py):
  a basic XY stage with properties
