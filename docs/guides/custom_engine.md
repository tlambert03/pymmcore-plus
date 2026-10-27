# Custom Acquisition Engines

!!! warning "Important"

    This page assumes you have a basic understanding of how the default MDA
    acquisition engine works to execute a sequence of `useq.MDAEvent` objects.
    If you haven't already done so, please read the [Acquisition
    Engine](./mda_engine.md) guide first.

While the default MDA acquisition engine is sufficient for many common use
cases, you may find that you need to customize it to accomplish your goals, for
example when:

- driving hardware for which a [Micro-Manager device
  adapter](https://micro-manager.org/Device_Support) does not exist,
- conditionally executing arbitrary python code before, during, or after
  each acquisition event,
- using an alternate [high-performance camera
  driver](https://github.com/acquire-project/acquire-python),
- handling user-specific [`MDAEvent.metadata`][useq.MDAEvent] values,
- intercepting and modifying the event sequence<sup>\*</sup>.

    !!! info "<sup>\*</sup>Note"

        If all you want is to modify the event sequence (e.g. to add
        additional events in a non-deterministic way) but you don't need to
        modify the behavior of the acquisition engine itself, you likely
        don't need to customize the acquisition engine. See the guide on
        [Event-Driven Acquisition](event_driven_acquisition.md) for details.

## The `MDARunner` and `MDAEngine`

Let's start by taking a quick look at how the acquisition logic in
pymmcore-plus is structured. There are two key classes involved:

1. An [**`MDARunner`**][pymmcore_plus.mda.MDARunner] instance is
   responsible for receiving a sequence of `useq.MDAEvent` objects and
   driving an `MDAEngine` to execute them. The `MDARunner` is the object that
   has the actual [`run()`][pymmcore_plus.mda.MDARunner.run] method. It also
   emits all the events, such as
   [`frameReady`][pymmcore_plus.mda.PMDASignaler.frameReady], and sends the
   images to the `output` (if any). Users shouldn't need to subclass or modify
   `MDARunner` directly.
1. An `MDAEngine` instance (anything that implements the
   [**`PMDAEngine`** protocol](#the-mdaengine-protocol)) is responsible for
   actually setting up and executing each event in the sequence. The default
   implementation of the `PMDAEngine` protocol is the
   [**`MDAEngine`**][pymmcore_plus.mda.MDAEngine] class, but you can register
   your own custom engine, using either a subclass of the default engine,
   or any other object that implements the `PMDAEngine` protocol.

```python
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus()

core.mda  # <- The MDARunner instance
core.mda.engine  # <- The MDAEngine instance
```

## The `MDAEngine` protocol

`pymmcore-plus` defines a protocol (a.k.a. "interface" in the Java world) that
all acquisition engines must implement. The [API
reference][pymmcore_plus.mda.PMDAEngine] has the formal details, but let's
discuss the three key methods here.

1. [`setup_sequence()`][pymmcore_plus.mda.PMDAEngine.setup_sequence] -
   Setup state of system before an MDA is run.
2. [`setup_event()`][pymmcore_plus.mda.PMDAEngine.setup_event] -
   Prepare state of system for an event.
3. [`exec_event()`][pymmcore_plus.mda.PMDAEngine.exec_event] -
   Execute the event.

!!! important "The `PMDAEngine` Protocol"

    ```python
    class MyEngine:
        def setup_sequence(self, sequence: MDASequence) -> SummaryMetaV1 | None:
            """Setup state of system (hardware, etc.) before an MDA is run.

            This method is called once at the beginning of a sequence.
            (The sequence object needn't be used here if not necessary)
            """

        def setup_event(self, event: MDAEvent) -> None:
            """Prepare state of system (hardware, etc.) for `event`.

            This method is called before each event in the sequence. It is
            responsible for preparing the state of the system for the event.
            The engine should be in a state where it can call `exec_event`
            without any additional preparation.  It may raise `SkipEvent`
            to skip this event.
            """

        def exec_event(
            self, event: MDAEvent
        ) -> Iterable[tuple[NDArray, MDAEvent, FrameMetaV1] | None]:
            """Execute `event`.

            This method is called after `setup_event` and is responsible for
            executing the event. The default assumption is to acquire an image,
            but more elaborate events will be possible.  Returns (or yields)
            an `(image, event, metadata)` tuple for each acquired frame.
            """
    ```

Your engine doesn't need to inherit from anything, but if you subclass
[`PMDAEngine`][pymmcore_plus.mda.PMDAEngine] itself, Python will refuse to create
it until these three methods are implemented.

The return value of `exec_event` is what the runner turns into data:

- It must be an iterable (a list, a tuple, or a generator that `yield`s) of
  `(image, event, metadata)` tuples, one per acquired frame.  For each tuple, the
  runner emits `frameReady(image, event, metadata)` and sends the frame to the
  `output`.
- Return an empty iterable (or `None`) if the event didn't produce an image.
- A `None` *inside* the iterable stands for a frame that should have been
  acquired, but wasn't (e.g. a camera that dropped a frame); the runner tells the
  data sink to leave a gap for it.

The following methods are optional, but will be used if they are defined:

1. [`event_iterator()`][pymmcore_plus.mda.PMDAEngine.event_iterator] -
   Optional wrapper on the event iterator. To customize the event sequence.
   (This is how the default engine merges events for [hardware
   triggering](mda_engine.md#hardware-triggered-sequences).  It isn't called
   when an *iterator*, such as a generator, is passed to the runner.)
2. [`teardown_event()`][pymmcore_plus.mda.PMDAEngine.teardown_event] -
   Called after `exec_event()`. To clean up after an event.
3. [`teardown_sequence()`][pymmcore_plus.mda.PMDAEngine.teardown_sequence] -
   Called after the sequence is complete. To clean up after an MDA.

!!! note "Saving data from your own engine"

    The data sink behind `output=` (see [Saving Data](saving_data.md)) uses the
    summary metadata returned by `setup_sequence` to learn the image size and
    dtype, and it reads `exposure_ms` from each frame's metadata.  Subclasses of
    `MDAEngine` get both for free.  If you yield your own frames, build their
    metadata with `self.get_frame_metadata(event)` (or, in an engine that doesn't
    subclass `MDAEngine`, with
    [`pymmcore_plus.metadata.frame_metadata`][pymmcore_plus.metadata.frame_metadata]
    and [`summary_metadata`][pymmcore_plus.metadata.summary_metadata]).  An empty
    dict works for `frameReady`, but fails with `KeyError: 'exposure_ms'` when
    saving.

## The built-in `MDAEngine`

The default implementation of the `PMDAEngine` protocol is the
[**`MDAEngine`**][pymmcore_plus.mda.MDAEngine] class. It can handle microscope
setup and image acquisition for a standard `MDAEvent` (see [what the engine
does](mda_engine.md#what-the-engine-does)), and opportunistically queues
[hardware-triggered sequences](mda_engine.md#hardware-triggered-sequences). It also serves as a good base
class for custom engines if you want to extend the default behavior. (You may
also find the [source
code](https://github.com/pymmcore-plus/pymmcore-plus/blob/main/src/pymmcore_plus/mda/_engine.py)
for the `MDAEngine` class helpful as a reference when writing a custom engine.)
Its `setup_event` and `exec_event` hand off to
[`setup_single_event`][pymmcore_plus.mda.MDAEngine.setup_single_event] /
[`exec_single_event`][pymmcore_plus.mda.MDAEngine.exec_single_event] for regular
events, and to
[`setup_sequenced_event`][pymmcore_plus.mda.MDAEngine.setup_sequenced_event] /
[`exec_sequenced_event`][pymmcore_plus.mda.MDAEngine.exec_sequenced_event] for
hardware-triggered ones, so you can override just the part you need.

## Customizing the `MDAEngine`

If you want to customize _how_ the instrument sets up or executes each event,
the easiest approach is to subclass the default `MDAEngine` class and override
or extend the methods you need to customize, then register your custom engine
with [`core.register_mda_engine()`][pymmcore_plus.CMMCorePlus.register_mda_engine].

```python
from collections.abc import Iterator

import numpy as np
import useq
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine


class MyEngine(MDAEngine):  # (1)!
    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-setup
        super().setup_event(event)  # (2)!
        # do some custom post-setup

    def exec_event(
        self, event: useq.MDAEvent
    ) -> Iterator[tuple[np.ndarray, useq.MDAEvent, dict] | None]:
        """Execute `event`."""
        # do some custom pre-execution
        yield from super().exec_event(event)  # (3)!
        # do some custom post-execution


core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# Register the custom engine with the runner
core.register_mda_engine(MyEngine(core))  # (4)!

# Run an MDA
core.mda.run([useq.MDAEvent()])
```

1. Create a custom engine by subclassing the default engine
2. Note that it's not required to call the `super()` methods here
   if you don't want to
3. The default `exec_event` is a *generator*: nothing is acquired until the
   runner iterates over it.  Using `yield from` keeps it that way, and makes your
   "post-execution" code run *after* the image has been acquired (and emitted).
   (If you wrote `return super().exec_event(event)` instead, any code between that
   call and the `return` would run *before* the image is acquired.)
4. Note that `MDAEngine.__init__` accepts a `CMMCorePlus` instance
   as its first argument, so you'll need to pass that in when
   instantiating your custom engine.

`register_mda_engine` sets `core.mda`'s engine (with
[`core.mda.set_engine()`][pymmcore_plus.mda.MDARunner.set_engine], which you may
also call directly), and then emits the
[`mdaEngineRegistered`][pymmcore_plus.PCoreSignaler.mdaEngineRegistered]
signal, which you can use to be alerted when someone swaps out the engine:

```python
@core.events.mdaEngineRegistered.connect
def on_new_engine(new_engine, old_engine):
    print("new engine registered!")
```

The engine can't be changed while an acquisition is running.

## Skipping an event

If `setup_event` finds that an event can't be done (a device didn't respond, a
position is out of reach, etc...), it may raise
[`SkipEvent`][pymmcore_plus.mda.SkipEvent].  The runner then skips `exec_event`
for that event (but still calls `teardown_event`), and tells the data sink to
leave a gap, so the rest of the data still lands in the right place:

```python
from pymmcore_plus.mda import MDAEngine, SkipEvent


class CarefulEngine(MDAEngine):
    def setup_event(self, event: useq.MDAEvent) -> None:
        if event.index.get("p") == 1:  # (1)!
            raise SkipEvent(reason="position 1 is out of reach")
        super().setup_event(event)
```

1. Any check you like.  For a hardware-triggered
   [`SequencedEvent`][pymmcore_plus.core.SequencedEvent], which stands for several
   frames, pass the number of frames to skip:
   `SkipEvent(num_frames=len(event.events))`.

## Utilizing `MDAEvent` metadata

More often than not, if you are customizing the acquisition engine, it will
be because you'd like to do something _other_ than drive the Micro-Manager
core to set up and acquire an image. Perhaps you need to control a micro-fluidic
device, or control a DAQ card, or communicate with a remote server, etc.

In all of these cases, you will likely need additional parameters (beyond
the fields defined in the `MDAEvent` class) to pass to your control code.
For this, the `MDAEvent` class has a `metadata` attribute that is explicitly
provided for user-defined data.

```python
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
import useq


class MyEngine(MDAEngine):
    def setup_event(self, event: useq.MDAEvent) -> None:
        if "my_key" in event.metadata:  # (1)!
            self._my_custom_setup(event.metadata["my_key"])
        else:
            super().setup_event(event)

    def _my_custom_setup(self, params: dict) -> None:
        print(f"Setting up my custom device with {params}")

    def exec_event(self, event: useq.MDAEvent):
        if "my_key" in event.metadata:
            return self._my_custom_exec(event.metadata["my_key"])  # (2)!
        return super().exec_event(event)

    def _my_custom_exec(self, params: dict) -> tuple:
        print(f"Executing my custom stuff with {params}")
        return ()  # no images from this event


core = CMMCorePlus.instance()
core.loadSystemConfiguration()

core.register_mda_engine(MyEngine(core))
core.mda.engine.use_hardware_sequencing = False  # (3)!

experiment = [
    useq.MDAEvent(),
    useq.MDAEvent(metadata={"my_key": {"param1": "val1"}}),  # (4)!
    useq.MDAEvent(),
    useq.MDAEvent(metadata={"my_key": {"param1": "val2"}}),
]

core.mda.run(experiment)
```

1. You can use any characteristics of the `MDAEvent`, such as the `index`, or
   the presence of a special key in the `metadata` attribute, to determine
   whether you want to do something special for that event.
2. You don't _have_ to return here. If you also want to do the default image
   acquisition, you can call `super().exec_event(event)` as well.
3. **Don't skip this.**  With hardware sequencing on (the default), the engine
   merges consecutive events that it can run as one hardware-triggered sequence,
   and it doesn't compare their `metadata` when deciding.  The four events above
   would be merged into a single `SequencedEvent` (with empty `metadata`), and
   neither of our custom branches would ever run.
4. Add metadata to the event. You can do this either by constructing your own
   sequence of `MDAEvent` objects, or by using
   [`MDASequence`](../../useq-schema/guides/sequences.md) to build
   the sequence for you, then editing the `metadata` attributes as needed.

... which prints:

```
Setting up my custom device with {'param1': 'val1'}
Executing my custom stuff with {'param1': 'val1'}
Setting up my custom device with {'param1': 'val2'}
Executing my custom stuff with {'param1': 'val2'}
```

!!! example

    For a real-world example of an `MDAEngine` subclass that uses
    `MDAEvent.metadata` to drive hardware for Raman spectroscopy,
    see Ian Hunt-Isaak's
    [raman-mda-engine](https://github.com/ianhi/raman-mda-engine).
    (engine subclass
    [here](https://github.com/ianhi/raman-mda-engine/blob/main/raman_mda_engine/_engine.py))
