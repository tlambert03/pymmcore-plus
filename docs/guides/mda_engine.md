# The Acquisition Engine

One of the key features of pymmcore-plus is the acquisition engine. This allows
you to define and execute a sequence of events. The sequence may be a typical
multi-dimensional acquisition (MDA), such as a z-stack across multiple channels,
stage positions, and time points; or it can be any custom sequence of events
that you define. It needn't even be a sequence of known length: you can define
an iterable or a [`queue.Queue`][] of events that reacts to the results of
previous events, for event-driven "smart" microscopy.

The built-in acquisition engine will support many standard use-cases, but you
can also subclass and customize it, allowing arbitrary python code to be
executed at each step of the acquisition. This makes it possible to incorporate
custom hardware control (e.g. to control devices for which Micro-Manager has no
adapters), data analysis, or other logic into the experiment.

There are two objects involved, and you'll see both names in these docs.  The
**runner**, [`core.mda`][pymmcore_plus.CMMCorePlus.mda] (an
[`MDARunner`][pymmcore_plus.mda.MDARunner]), is what you call.  It walks through
the events (waiting until each one is due, and handling pause and cancel), emits
signals such as `frameReady`, and sends the images to wherever you asked it to
save them.  The **engine**, `core.mda.engine` (an
[`MDAEngine`][pymmcore_plus.mda.MDAEngine], unless you've replaced it), is what
actually drives the hardware for each event (moving the stages, setting the
channel and exposure, and snapping the image).

## Running a very simple sequence

To execute a sequence, you must:

1. Create a [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] instance (and probably
   load a configuration file)
2. Pass an iterable of [`useq.MDAEvent`][] objects to the
   [`run_mda()`][pymmcore_plus.CMMCorePlus.run_mda] method.

```python
from pymmcore_plus import CMMCorePlus
from useq import MDAEvent

# Create the core instance.
mmc = CMMCorePlus.instance()  # (1)!
mmc.loadSystemConfiguration()  # (2)!

# Create a super-simple sequence, with one event
mda_sequence = [MDAEvent()]  # (3)!

# Run it!
mmc.run_mda(mda_sequence)
```

1. Here, we use the global
   [`CMMCorePlus.instance`][pymmcore_plus.CMMCorePlus.instance] singleton.
2. This loads the demo configuration by default.  Pass the path to your own
   config file to load that instead (see
   [`CMMCorePlus.loadSystemConfiguration`][pymmcore_plus.CMMCorePlus.loadSystemConfiguration]).
3. An experiment is just an iterable of [`useq.MDAEvent`][] objects.

!!! Tip

    [`CMMCorePlus.run_mda`][pymmcore_plus.CMMCorePlus.run_mda] is
    a convenience method that runs the experiment in a separate thread, and
    returns that [`Thread`][threading.Thread] right away (call `.join()` on it, or
    pass `block=True`, to wait for the acquisition to finish).  If you want to run
    it in the current thread, use
    [`CMMCorePlus.mda.run`][pymmcore_plus.mda.MDARunner.run] directly, which
    blocks until the acquisition is done:

    ```py
    mmc.mda.run(mda_sequence)
    ```

The code above will execute a single, very boring event! It will snap
one image (the default action of an `MDAEvent`) with the current exposure
time, channel, stage position, etc... and then stop.

Let's make it a little more interesting.

## The `MDAEvent` object

The [`useq.MDAEvent`][] object is the basic building block of an experiment. It
is a relatively simple dataclass that defines a single action to be performed.
For complete details, see the [useq-schema
documentation](../../useq-schema/schema/event.md), but
some key attributes you might want to set are:

- **exposure** (`float`): The exposure time (in milliseconds) to use for this
  event.
- **channel** ([`Channel`][useq.EventChannel]): The configuration preset to
  use.  May be given as a `str` (the name of a preset in the `Channel` group), or
  as a `dict` with two keys: `config` and `group` (the preset and configuration
  group, respectively).
- **x_pos**, **y_pos**, **z_pos** (`float`): An `x`, `y`, and `z` stage position
  to use for this event.
- **min_start_time** (`float`): The minimum time to wait before starting this
  event, in seconds, relative to the start of the sequence (or to the last event
  that had `reset_event_timer=True`).

!!! example

    ```python
    snap_a_dapi = MDAEvent(channel="DAPI", exposure=100, x_pos=1100, y_pos=1240)
    ```

    **NOTE:** The name `"DAPI"` here must be a name of a
    [preset](https://micro-manager.org/Micro-Manager_Configuration_Guide#configuration-presets)
    in your Micro-Manager "Channel" configuration group.

For any missing keys, the implied meaning is "use the current setting". For
example, an `MDAEvent` without an `x_pos` or a `y_pos` will use the current
stage position.

The implied "action" of an `MDAEvent` is to snap an image.  Events can carry
other actions too (see [what the engine does](#what-the-engine-does)).

## A multi-event sequence

With our understanding of `MDAEvent` objects, we can now create a slightly more
interesting experiment. This one will snap four images: two channels at two
different stage positions.

```python
from pymmcore_plus import CMMCorePlus
from useq import MDAEvent

# Create the core instance.
mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration()

# Snap two channels at two positions
mda_sequence = [
    MDAEvent(channel={"config": "DAPI"}, x_pos=1100, y_pos=1240),
    MDAEvent(channel={"config": "FITC"}, x_pos=1100, y_pos=1240),
    MDAEvent(channel={"config": "DAPI"}, x_pos=1442, y_pos=1099),
    MDAEvent(channel={"config": "FITC"}, x_pos=1442, y_pos=1099),
]

# Run it!
mmc.run_mda(mda_sequence)
```

!!! info "Logs"

    By default, only warnings and errors are printed to the console.  If you set
    the environment variable `PYMM_LOG_LEVEL=INFO` before running the code above,
    you will also see each event as it is executed:

    ```log
    2026-10-27 00:20:41,785 - pymmcore-plus - INFO - (_runner.py:677) MDA Started: GeneratorMDASequence()
    2026-10-27 00:20:41,785 - pymmcore-plus - INFO - (_runner.py:553) channel=Channel(config='DAPI') x_pos=1100.0 y_pos=1240.0
    2026-10-27 00:20:41,972 - pymmcore-plus - INFO - (_runner.py:553) channel=Channel(config='FITC') x_pos=1100.0 y_pos=1240.0
    2026-10-27 00:20:41,997 - pymmcore-plus - INFO - (_runner.py:553) channel=Channel(config='DAPI') x_pos=1442.0 y_pos=1099.0
    2026-10-27 00:20:42,052 - pymmcore-plus - INFO - (_runner.py:553) channel=Channel(config='FITC') x_pos=1442.0 y_pos=1099.0
    2026-10-27 00:20:42,077 - pymmcore-plus - INFO - (_runner.py:762) MDA Finished: GeneratorMDASequence()
    ```

    See [logging](logging.md) for more details on how to configure and review logs.

At this point, you might be thinking that constructing a sequence by hand is a
little tedious. And you'd be right! That's why we have the
`MDASequence` class.

## Building sequences with `MDASequence`

For most standard multi-dimensional experiments, you will want to use
[`useq.MDASequence`][] to construct your sequence of events. It allows you to
declare a "plan" for each axis in your experiment (channels, time, z, etc...)
along with the order in which the axes should be iterated:

```python
import useq

mda_sequence = useq.MDASequence(
    time_plan={"interval": 2, "loops": 6},  # 6 time points, 2 seconds apart
    channels=[
        {"config": "DAPI", "exposure": 50},
        {"config": "FITC", "exposure": 80},
    ],
)
```

`MDASequence` comes from useq-schema, which has its own guide:
[Building Sequences](../../useq-schema/guides/sequences.md) walks through
z-stacks, grids, skipping channels at some time points, per-position settings,
and saving sequences to (and loading them from) YAML or JSON files.

## Running an MDA sequence

Calling `list()` on an instance of `MDASequence` gives you a list of `MDAEvent`
objects. This means that `MDASequence` **_is_** an
[iterable](https://docs.python.org/3/glossary.html#term-iterable) of
`MDAEvent`... which is exactly what we need to pass to the
[`run_mda()`][pymmcore_plus.CMMCorePlus.run_mda] method.

So, you can directly pass an instance of `MDASequence` to `run_mda`:

```python
from pymmcore_plus import CMMCorePlus
import useq

mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration()

# create a sequence
mda_sequence = useq.MDASequence(
    stage_positions=[{"z": mmc.getZPosition()}],  # (1)!
    time_plan={"interval": 2, "loops": 10},
    z_plan={"range": 4, "step": 0.5},
    channels=[
        {"config": "DAPI", "exposure": 50},
        {"config": "FITC", "exposure": 20},
    ],
)

# Run it!
mmc.run_mda(mda_sequence)
```

1. A `range` z plan is *relative* to the `z` of each stage position, so here we
   use the current focus position.  Without a position, the stack would be
   centered on z = 0, *not* on the current focus (see [Relative to
   what?](../../useq-schema/guides/sequences.md#a-z-stack-at-three-positions)).

## Handling acquired data

You will almost certainly want to _do_ something with the
data that is collected during an MDA :joy:.

To save it to disk, pass `output=` with a path ending in `.ome.zarr` or
`.ome.tiff`:

```python
mmc.mda.run(mda_sequence, output="experiment.ome.zarr")
```

[Saving Data](saving_data.md) explains the formats, what you get on disk, how to
read it back, and how to control the details.

You will also want to know how to connect callbacks to the
[`frameReady`][pymmcore_plus.mda.PMDASignaler.frameReady] event, so that you can
handle incoming data as it is acquired:

```python
from pymmcore_plus import CMMCorePlus
import numpy as np
import useq

mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration()


@mmc.mda.events.frameReady.connect  # (1)!
def on_frame(image: np.ndarray, event: useq.MDAEvent, metadata: dict):
    # do what you want with the data
    print(
        f"received frame: {image.shape}, {image.dtype} "
        f"@ index {event.index}, z={event.z_pos}"
    )


mda_sequence = useq.MDASequence(
    stage_positions=[{"z": mmc.getZPosition()}],
    time_plan={"interval": 0.5, "loops": 10},
    z_plan={"range": 4, "step": 0.5},
)

mmc.run_mda(mda_sequence)
```

1. The `frameReady` signal accepts a callback with up to three arguments:
   the image data as a numpy array, the `MDAEvent` that triggered the callback,
   and a dict of frame metadata (see
   [`FrameMetaV1`][pymmcore_plus.metadata.FrameMetaV1]).

This callback is called in the acquisition thread, so the next event waits for it
to finish (see [Threads and callbacks](#threads-and-callbacks) below).  See also
[additional events you may wish to connect to](../reference/events.md).

## Cancelling or pausing

You can pause or cancel the acquisition with the
[`CMMCorePlus.mda.set_paused`][pymmcore_plus.mda.MDARunner.set_paused]
or [`CMMCorePlus.mda.cancel`][pymmcore_plus.mda.MDARunner.cancel]
methods.

```python
mmc.mda.set_paused(True)   # pauses the mda
mmc.mda.set_paused(False)  # resumes the mda

mmc.mda.cancel()  # cancels the mda
```

Both take effect between events.  (A hardware-triggered sequence, described
below, can be cancelled while it runs, but not paused.)

## What the engine does

When a run starts, the default engine's
[`setup_sequence`][pymmcore_plus.mda.MDAEngine.setup_sequence] stops live mode
(if it's running), applies the sequence's `setup` event (if any), and fills in
the field of view of grid plans that don't specify one, from the camera ROI and
pixel size.

Then, for each event, the runner waits until the event's `min_start_time` and
emits [`eventStarted`][pymmcore_plus.mda.PMDASignaler.eventStarted], and the
engine's [`setup_event`][pymmcore_plus.mda.MDAEngine.setup_event]:

1. moves the XY stage to `x_pos`/`y_pos`, then the focus stage to `z_pos` (plus
   any correction found by an earlier hardware autofocus event at that position),
2. sets the SLM image, if there is one,
3. sets the channel preset (skipped if it's the same preset as last time),
4. sets the exposure, any `properties`, and the camera ROI,
5. turns off autoshutter and opens the shutter, if the event asks to
   `keep_shutter_open`,

and then calls `waitForSystem()`.  Anything that is `None` on the event is left
as it is.  [`exec_event`][pymmcore_plus.mda.MDAEngine.exec_event] then calls
`snapImage()`, and `getImage()` for each camera channel (more than one with a
Multi Camera device), and the runner emits `frameReady` for each image.  A
`HardwareAutofocus` action runs `fullFocus()` instead of acquiring an image, and
the default engine doesn't acquire anything for other actions (such as a
`CustomAction`).

!!! warning "The engine puts things back"

    At the end of a run, the default engine returns the XY stage, focus, exposure,
    configuration presets, autoshutter and camera ROI to where they were when the
    run started (moving Z and XY in whichever order keeps the objective away from
    the sample).  This is only done automatically when the focus direction of your
    focus stage is known (`FocusDirection` in your config file, or "Stage Focus
    Direction" in the Hardware Configuration Wizard).  To choose for yourself, set
    [`restore_initial_state`][pymmcore_plus.mda.MDAEngine.restore_initial_state]:

    ```python
    mmc.mda.engine.restore_initial_state = False  # leave everything where the MDA put it
    ```

## Hardware-triggered sequences

Having the computer "in-the-loop" for every event in an MDA sequence can add
unwanted overhead that limits performance in rapid acquisition sequences.
Because of this, some devices support _hardware triggering_. This means that the
computer can tell the device to queue up and start a sequence of events, and the
device will take care of executing the sequence without further input from the
computer.

Just like [Micro-Manager's acquisition
engine](https://micro-manager.org/Hardware-based_Synchronization_in_Micro-Manager),
the default acquisition engine in `pymmcore-plus` can opportunistically use
hardware triggering whenever possible.  Consecutive events are merged into a
single [`SequencedEvent`][pymmcore_plus.core.SequencedEvent] when the things
that change between them (exposure, XY position, Z position, SLM image, or any
property in the channel preset or in the event's `properties`) can be
sequenced by your hardware, and the sequence fits within each device's maximum
sequence length.  The camera then runs a sequence acquisition, and the frames are
read from the buffer as they arrive.

A few things always end a hardware-triggered sequence:

- a new time point with a different `min_start_time`.  So time-lapses with an
  interval are never merged across time points (only `"interval": 0` bursts are);
- a change of camera ROI;
- an event with an action other than acquiring an image (e.g. hardware autofocus);
- a change of a stage `Position` set through the event's `properties`.

Events are also *never* merged when you pass an *iterator* to the runner (a
generator, or a queue-backed iterator as in [event-driven
acquisition](event_driven_acquisition.md)), rather than a list or an
`MDASequence`.  In that case, the engine doesn't get to look ahead.

This behavior is on by default, but you can disable it by setting
`CMMCorePlus.mda.engine.use_hardware_sequencing = False`, which may be useful
for various debugging or testing purposes (or when your events carry
`metadata` that a [custom engine](custom_engine.md#utilizing-mdaevent-metadata)
needs to see one event at a time):

```python
mmc.mda.engine.use_hardware_sequencing = False  # default is True
```

!!! question "How does pymmcore-plus know if my device supports hardware triggering?"

    The low-level `CMMCore` object itself has a number of methods that query
    whether certain devices are capable of hardware triggering, such as

    - [`pymmcore.CMMCore.isStageSequenceable`][]
    - [`pymmcore.CMMCore.isPropertySequenceable`][]
    - [`pymmcore.CMMCore.isXYStageSequenceable`][]
    - [`pymmcore.CMMCore.isExposureSequenceable`][]

    Hint: Many devices that support sequencing have a property (often named
    `Sequence` or similar) that can be used to toggle their responses to the
    above queries, thereby enabling or disabling sequencing.

    To see how the engine will group your events, pass them (with your
    configuration loaded) to
    [`iter_sequenced_events`][pymmcore_plus.core.iter_sequenced_events], which is
    what the engine uses:

    ```python
    from pymmcore_plus import CMMCorePlus
    from pymmcore_plus.core import iter_sequenced_events
    import useq

    mmc = CMMCorePlus.instance()
    mmc.loadSystemConfiguration()

    z_stack = useq.MDASequence(z_plan={"range": 2, "step": 1}, stage_positions=[{"z": 0}])
    print(list(iter_sequenced_events(mmc, z_stack)))
    # [MDAEvent(index={'p': 0, 'z': 0}, z_pos=-1.0), MDAEvent(...), MDAEvent(...)]

    mmc.setProperty("Z", "UseSequences", "Yes")  # the demo Z stage can be sequenced
    print(list(iter_sequenced_events(mmc, z_stack)))
    # [SequencedEvent(z_pos=-1.0, properties=[], z_sequence='(3 items)')]
    ```

## Threads and callbacks

The `mmc.mda.events` signals are emitted from the acquisition thread, and (with
the default psygnal backend) the next event waits for your `frameReady` callbacks
to return.  So keep them quick, or pass a handler object to `output=` instead,
which runs on its own thread (see [Saving
Data](saving_data.md#processing-frames-yourself)).  [Threads](events.md#threads)
explains which thread your callbacks run in, and how the Qt backend changes that.

## A complete example

Here is a script that puts most of the above together.  Run it with `--zarr` or
`--tiff` to also save the data:

```python linenums="1" title="run_mda.py"
--8<-- "examples/run_mda.py"
```

1. Access the global singleton:
   [`CMMCorePlus.instance`][pymmcore_plus.CMMCorePlus.instance]
2. See
   [`CMMCorePlus.loadSystemConfiguration`][pymmcore_plus.CMMCorePlus.loadSystemConfiguration]
3. See [Building Sequences](../../useq-schema/guides/sequences.md) for the many
   ways to describe an experiment with [`useq.MDASequence`][].
4. The z plan is relative to this position's `z`, so the stack is centered on
   the current focus position.
5. For info on all of the signals available to connect to, see
   [Events](../reference/events.md).
6. `mda.run` blocks until the acquisition is done.  Use
   [`mmc.run_mda(sequence)`][pymmcore_plus.CMMCorePlus.run_mda] to run it on a
   new thread instead.

## Next steps

Now that you have a basic understanding of how to create and run
multi-dimensional acquisition sequences in pymmcore-plus, you may want to
take a look at some more advanced features:

- [saving data](saving_data.md) to OME-Zarr or OME-TIFF
- [creating non-deterministic sequences for event-driven
  acquisition](event_driven_acquisition.md)
- [customizing the acquisition engine](custom_engine.md)
