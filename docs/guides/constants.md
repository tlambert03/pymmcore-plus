# Constants

All of the constants in the `pymmcore` library are in the top level
`pymmcore` namespace, making it a bit difficult to know what type
or enumeration they refer to.

All of these constants are reimplemented in the `pymmcore_plus` library
as enums ([`enum.IntEnum`][] or [`enum.StrEnum`][]) and are available in the
`pymmcore_plus` namespace (and are listed below).

For example, the integer corresponding to the `AfterLoadSequence` action type
could be accessed as `pymmcore.AfterLoadSequence` or
`pymmcore_plus.ActionType.AfterLoadSequence`.

```python
In [1]: import pymmcore

In [2]: pymmcore.AfterLoadSequence
Out[2]: 4

In [3]: from pymmcore_plus import ActionType

In [4]: ActionType.AfterLoadSequence
Out[4]: <ActionType.AfterLoadSequence: 4>

In [5]: int(ActionType.AfterLoadSequence)
Out[5]: 4
```

Additionally, it becomes easier to see what constants are available for
each type or enumeration.

```python
In [6]: list(ActionType)
Out[6]:
[
    <ActionType.NoAction: 0>,
    <ActionType.BeforeGet: 1>,
    <ActionType.AfterSet: 2>,
    <ActionType.IsSequenceable: 3>,
    <ActionType.AfterLoadSequence: 4>,
    <ActionType.StartSequence: 5>,
    <ActionType.StopSequence: 6>
]
```

Lastly, many of the methods that return integers in `pymmcore.CMMCore`
have been re-implemented in `pymmcore_plus.CMMCorePlus` to return the
appropriate enumeration.

```python
import pymmcore

core = pymmcore.CMMCore()
# ...  load config and devices
core.getDeviceType("Camera")  # 2


import pymmcore_plus

core = pymmcore_plus.CMMCorePlus()
# ...  load config and devices
core.getDeviceType("Camera")  # <DeviceType.CameraDevice: 2>
```

::: pymmcore_plus.DeviceType
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.PropertyType
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.FocusDirection
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.ActionType
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.PortType
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.DeviceDetectionStatus
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.DeviceInitializationState
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.PixelFormat
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.Keyword
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.CFGCommand
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

::: pymmcore_plus.CFGGroup
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false
