# Events and Callbacks

!!! warning "Terminology confusion!"

    A quick warning on terminology: the name "event" may refer to two different
    things in pymmcore-plus, which are not to be confused.

    This page discusses the "events" that are emitted by the `CMMCorePlus` and
    `MDARunner` objects.  These are occurrences that your program can react to
    by registering callback functions. These are also known as "**signals**" in the
    context of the Qt framework or psygnal.

    The term "event" may also be used to refer to the **`useq.MDAEvent`** objects that
    are consumed by the [Acquisition Engine](../guides/mda_engine.md).
    These are *not* the same as the "events" discussed on this page.

Both the [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] object and the
[`CMMCorePlus.mda`][pymmcore_plus.CMMCorePlus.mda] (`MDARunner`) objects have
`events` attributes that can be used to register callbacks for events that occur
as the state of the microscope changes, or as an acquisition sequence progresses.

## Event backends

`pymmcore-plus` supports both **Qt**-based and
[**psygnal**](https://github.com/pyapp-kit/psygnal)-based event signaling.

**The default behavior is to use Qt-backed signals when a global `QApplication`
instance exists at the time the `CMMCorePlus` object is created, and `psygnal`
otherwise.**  The backend is chosen once, when the core is created, so if you're
building a Qt application, create the `QApplication` *before* the `CMMCorePlus`.
(The difference matters mostly for [threads](#threads), see below.)

If you would like to force a specific event backend, you can do so by
setting the `PYMM_SIGNALS_BACKEND` environment variable to `qt`,
`psygnal`, or `auto` (for the default behavior).

=== "bash/zsh"

    ```bash
    export PYMM_SIGNALS_BACKEND=psygnal
    ```

=== "cmd"
    ```cmd
    set PYMM_SIGNALS_BACKEND=psygnal
    ```

=== "python"
    ```python
    # before instantiating CMMCorePlus
    import os

    os.environ["PYMM_SIGNALS_BACKEND"] = "psygnal"
    ```

=== "powershell"
    ```powershell
    $env:PYMM_SIGNALS_BACKEND = "psygnal"
    ```

## Connecting callbacks to events

To connect a callback to an event, use the `connect` method of the specific
event emitter that you would like to listen to.  (All event backends
support the same connection/disconnection API.)

!!!example "Example: Connecting callbacks"
    Given a `CMMCorePlus` object `core`:

    ```python
    import numpy as np
    import useq

    from pymmcore_plus import CMMCorePlus

    core = CMMCorePlus()
    ```

    Register a callback to listen to property changes on the `CMMCorePlus`:

    ```python
    @core.events.propertyChanged.connect
    def on_property_changed(dev: str, prop: str, value: str):
        print(f"Property {prop!r} on device {dev!r} changed to {value}")
    ```

    Register a callback to process data during an acquisition sequence:

    ```python
    @core.mda.events.frameReady.connect
    def on_image_captured(data: np.ndarray, event: useq.MDAEvent, metadata: dict):
        print(f"Event index {event.index} captured with shape {data.shape}")
    ```

The signature of the callback function should match the signature of the event
emitter's signal (although it may accept *fewer* arguments than the signal emits,
in which case the extra ones are dropped).  The available events and their
signatures are listed in the [events reference](../reference/events.md), and
are defined by two protocols:

- [`PCoreSignaler`][pymmcore_plus.PCoreSignaler]: events emitted at `CMMCorePlus.events`
  when the state of the microscope changes.
- [`PMDASignaler`][pymmcore_plus.mda.PMDASignaler]: events emitted at
  `CMMCorePlus.mda.events` as an acquisition sequence progresses.

You may **disconnect** a callback from an event by calling the `disconnect` method
of the event emitter with the callback function as the argument.

!!!example "Example: Disconnecting callbacks"
    ```python
    core.events.propertyChanged.disconnect(on_property_changed)
    ```

### Listening to a single device or property

`propertyChanged` fires for every property on every device.  If you only care
about one device (or one property on one device), use
[`devicePropertyChanged`][pymmcore_plus.PCoreSignaler.devicePropertyChanged].
Note that the callback then receives fewer arguments:

```python
def on_gain_changed(value: str):
    print(f"Gain is now {value}")


def on_camera_changed(prop: str, value: str):
    print(f"Camera {prop} is now {value}")


# called with (value) when the camera's Gain changes
core.events.devicePropertyChanged("Camera", "Gain").connect(on_gain_changed)

# called with (property_name, value) when any camera property changes
core.events.devicePropertyChanged("Camera").connect(on_camera_changed)
```

## Threads

[`run_mda`][pymmcore_plus.CMMCorePlus.run_mda] runs the acquisition on a new
thread, and all of the `core.mda.events` signals are emitted from that thread.
(`core.mda.run()` blocks and runs the acquisition in the thread you called it
from, so the signals are emitted there.)  What happens next depends on the event
backend:

- With **psygnal**, callbacks are called synchronously, *in the acquisition
  thread*.  A slow `frameReady` callback will delay the next event, so do heavy
  processing elsewhere (handler objects passed to `output=` are called from a
  separate thread, so they don't hold up the acquisition).  Don't touch Qt
  widgets from these callbacks.
- With **Qt**, callbacks connected from the main thread are delivered on the main
  thread (through Qt's event loop), which is what you want for updating a GUI.

The same goes for `core.events`: with psygnal, callbacks run in whichever thread
made the change (usually yours, but some device adapters notify the core from
their own threads).

See [processing frames yourself](saving_data.md#processing-frames-yourself) for
handing frames off to another thread.

## Following changes in the core

Here's a small script that reacts to a change in the microscope's state (the same
pattern you'd use to keep a GUI in sync with the hardware):

```python linenums="1" title="properties_and_state_events.py"
--8<-- "examples/properties_and_state_events.py"
```

... which prints `new objective is Nikon 20X Plan Fluor ELWD`.

!!! note "State devices emit two events"

    When a state device (like a filter wheel or objective turret) changes, *two*
    `propertyChanged` events are emitted: one for the `State` property and one for
    the `Label` property.

    ```text
    propertyChanged: Objective State 3
    propertyChanged: Objective Label Nikon 20X Plan Fluor ELWD
    ```

    So it's usually best to check the property name and only respond to one of
    them, as the example above does.
