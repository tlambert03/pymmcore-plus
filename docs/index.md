# pymmcore-plus

`pymmcore-plus` aims to extend
[pymmcore](https://github.com/micro-manager/pymmcore) (Python bindings for the
C++ [Micro-Manager core](https://github.com/micro-manager/mmCoreAndDevices/))
with a number of features designed to facilitate working with Micro-Manager in
pure Python/C environments.  The main object in this library,
[`CMMCorePlus`][pymmcore_plus.CMMCorePlus], aims to be a drop-in replacement for
`pymmcore.CMMCore`, while adding a number of additional features including:

- A multi-dimensional [acquisition engine](guides/mda_engine.md) implemented in
  pure Python.  (The existing acquisition engines in Micro-Manager are written in
  Java and Clojure.)
- More flexible [event](guides/events.md) connections and callback handling.
- Extended convenience APIs for working with the core (which would be hard or
  impossible to implement in the `pymmcore` SWIG wrapper).
- More pythonic APIs for various pymmcore objects (e.g.
  [`Device`][pymmcore_plus.Device],
  [`Configuration`][pymmcore_plus.Configuration]) and
  [constants](guides/constants.md).

## Where to start

If you're new here, start with [Installation](../getting-started/install.md)
(which includes getting the [Micro-Manager device adapters](install.md)), then
[First steps](../getting-started/first-steps.md) and
[Your first acquisition](../getting-started/first-acquisition.md).  The User
Guide goes into more depth on [devices and properties](guides/devices.md),
[configuration groups](guides/configuration.md),
[events](guides/events.md), [running acquisitions](guides/mda_engine.md) and
[saving data](guides/saving_data.md).

## Reference

- [`CMMCorePlus`][pymmcore_plus.CMMCorePlus]: every method of the core, with
  what `pymmcore-plus` adds or overrides marked.
- [`pymmcore_plus.mda`][]: the acquisition runner
  ([`MDARunner`][pymmcore_plus.mda.MDARunner]) and engine
  ([`MDAEngine`][pymmcore_plus.mda.MDAEngine]).
- [Events](reference/events.md): the signals emitted by `core.events` and
  `core.mda.events`.
- [Metadata schema][pymmcore_plus.metadata]: the metadata dicts that come with
  each acquired frame.
- [Constants](guides/constants.md): the enums that replace pymmcore's integer
  constants.
- [Command line (`mmcore`)](cli.md) and
  [environment variables](env_var.md).
