# Device & Property objects

`pymmcore-plus` offers two classes that provide a more **object-oriented** interface
to common operations and queries performed on devices and their properties.

In the original `CMMCore` API, there are a lot of methods that accept a
`deviceLabel` string as the first argument (and perhaps additional arguments)
and query something about that device (e.g.
[`getDeviceLibrary`][pymmcore_plus.CMMCorePlus.getDeviceLibrary],
[`getDeviceType`][pymmcore_plus.CMMCorePlus.getDeviceType],
[`waitForDevice`][pymmcore_plus.CMMCorePlus.waitForDevice], etc...).  In `pymmcore-plus`, the
[`Device`][pymmcore_plus.Device] class acts as a "view" onto a specific device, and
these methods are implemented as methods (that no longer require the `deviceLabel` argument),
and the `deviceLabel` is passed to the constructor.

Similarly, there are many methods in the `CMMCore` API that require both a
device label and a device property name, and modify that specific property (e.g.
[`isPropertySequenceable`][pymmcore_plus.CMMCorePlus.isPropertySequenceable],
[`getProperty`][pymmcore_plus.CMMCorePlus.getProperty],
[`isPropertyReadOnly`][pymmcore_plus.CMMCorePlus.isPropertyReadOnly], etc...).  Here, the
[`DeviceProperty`][pymmcore_plus.DeviceProperty] class acts as a "view" onto a specific
device property, with an object-oriented interface to these methods.

```python
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus()
core.loadSystemConfiguration()  # demo config

camera = core.getDeviceObject("Camera")
print(camera.type(), camera.library())  # Camera DemoCamera

exposure = camera.getPropertyObject("Exposure")
exposure.value = 42
print(exposure.value, exposure.isReadOnly(), exposure.range())  # 42.0 False (0.0, 10000.0)
```

!!! tip "API reference"

    See [`Device`][pymmcore_plus.Device],
    [`DeviceProperty`][pymmcore_plus.DeviceProperty], and
    [`DeviceAdapter`][pymmcore_plus.DeviceAdapter] for the full API.

## Property info

[`DeviceProperty.dict()`][pymmcore_plus.DeviceProperty.dict] returns all
information about a property as a typed dictionary:

::: pymmcore_plus.core._property.InfoDict
    options:
      heading_level: 3
      show_root_full_path: false
