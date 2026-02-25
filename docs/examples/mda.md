# Multidimensional Acquisition

A key feature of `pymmcore-plus` is its [Multidimensional Acquisition (MDA)
engine](../guides/mda_engine.md)

The MDA engine is responsible for executing sequences of events defined using
[useq-schema](https://github.com/pymmcore-plus/useq-schema).

```python linenums="1" title="run_mda.py"
--8<-- "examples/run_mda.py"
```

<!-- These comments correspond to the (1), (2) annotations in run_mda.py. -->

1. `pymmcore-plus` uses
   [`useq-schema`](https://pymmcore-plus.github.io/useq-schema/) to define
   experimental sequences. You can either construct a [`useq.MDASequence`][]
   object manually, or
   [from a YAML/JSON file](https://pymmcore-plus.github.io/useq-schema/#serialization-and-deserialization).
2. Access global singleton:
   [`CMMCorePlus.instance`][pymmcore_plus.CMMCorePlus.instance]
3. See
   [`CMMCorePlus.loadSystemConfiguration`][pymmcore_plus.CMMCorePlus.loadSystemConfiguration]
4. For info on all of the signals available to connect to, see the
   [MDA Events API][pymmcore_plus.mda.events.PMDASignaler]
5. To avoid blocking further execution,
   [`run_mda`][pymmcore_plus.CMMCorePlus.run_mda] runs on a new thread.
   (`run_mda` returns a reference to the thread in case you want to do
   something with it, such as wait for it to finish with
   [threading.Thread.join][])

## Cancelling or Pausing

You can pause or cancel the mda with the
[`CMMCorePlus.mda.set_paused`][pymmcore_plus.mda.MDARunner.set_paused]
or [`CMMCorePlus.mda.cancel`][pymmcore_plus.mda.MDARunner.cancel]
methods.

## Customizing the MDA Engine

By default the built-in [`MDAEngine`][pymmcore_plus.mda.MDAEngine] will be used
to run the MDA. However, you can create a custom acquisition engine and register
it use
[`CMMCorePlus.register_mda_engine`][pymmcore_plus.CMMCorePlus.register_mda_engine].
See the [Custom Acquisition Engines](../guides/custom_engine.md) for more
details on how to do this.

You can be alerted to the the registering of a new engine with the
[`core.events.mdaEngineRegistered`][pymmcore_plus.core.events._protocol.PCoreSignaler.mdaEngineRegistered]
signal.

```python
@mmc.events.mdaEngineRegistered
def new_engine(new_engine, old_engine):
    print('new engine registered!")
```
