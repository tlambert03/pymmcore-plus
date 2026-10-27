# Devices and Properties

`pymmcore-plus` offers two classes that provide a more *object-oriented* interface
to common operations and queries performed on devices and their properties.

In the original `CMMCore` API, there are a lot of methods that accept a
`deviceLabel` string as the first argument (and perhaps additional arguments)
and query something about that device (e.g.
[`getDeviceLibrary`][pymmcore_plus.CMMCorePlus.getDeviceLibrary],
[`getDeviceType`][pymmcore_plus.CMMCorePlus.getDeviceType],
[`waitForDevice`][pymmcore_plus.CMMCorePlus.waitForDevice], etc...).  In `pymmcore-plus`, the
[`Device`][pymmcore_plus.Device] class acts as a "view" onto a specific device.  You
pass the `deviceLabel` once (to the constructor), and these become methods that no
longer need it.

Similarly, there are many methods in the `CMMCore` API that require both a
device label and a device property name, and query or modify that property (e.g.
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

To loop over the loaded devices or properties (optionally filtered by type, label,
etc...), use [`iterDevices`][pymmcore_plus.CMMCorePlus.iterDevices] and
[`iterProperties`][pymmcore_plus.CMMCorePlus.iterProperties], which yield these
same objects:

```python
from pymmcore_plus import DeviceType

[dev.label for dev in core.iterDevices(DeviceType.Stage)]  # ['Z']
[prop.name for prop in core.iterProperties(device_label="Camera", has_limits=True)]
```

See [`Device`][pymmcore_plus.Device],
[`DeviceProperty`][pymmcore_plus.DeviceProperty] and
[`DeviceAdapter`][pymmcore_plus.DeviceAdapter] (the same idea, for a device
adapter library) for the full API.

## Property info

[`DeviceProperty.dict()`][pymmcore_plus.DeviceProperty.dict] returns everything
about a property at once.  Continuing the example above:

```python
>>> exposure.dict()
{'valid': True,
 'value': 42.0,
 'type': 'number',
 'device_type': 'CameraDevice',
 'read_only': False,
 'sequenceable': False,
 'sequence_max_length': None,
 'pre_init': False,
 'range': (0.0, 10000.0),
 'allowed_values': ()}
```

(`range` is `None` for properties without limits, and `allowed_values` lists the
choices for properties that have them, like the camera's `Binning`.)

## Temporarily changing settings

You may want to temporarily set something on the core (for example
`core.setAutoShutter(False)` when writing an [MDA engine](custom_engine.md)) and
put it back afterwards.  For this case you can use the convenience method
[`CMMCorePlus.setContext`][pymmcore_plus.CMMCorePlus.setContext]:

```python
with core.setContext(exposure=100, autoShutter=False):
    print(core.getExposure(), core.getAutoShutter())  # 100.0 False
    core.snapImage()

print(core.getExposure(), core.getAutoShutter())  # back to the original values
```

This works for any name that has matching `get<Name>` and `set<Name>` methods on
the core (e.g. `exposure`, `autoShutter`, `shutterOpen`, `channelGroup`,
etc...).  The original values are restored when the `with` block exits, even if
an exception was raised inside it.
