# Overview

`pymmcore-plus` aims to extend
[pymmcore](https://github.com/micro-manager/pymmcore) (python bindings for the
C++ [micro-manager core](https://github.com/micro-manager/mmCoreAndDevices/))
with a number of features designed to facilitate working with **Micro-manager in
pure python/C environments**.

- `pymmcore-plus` itself is a superset of
  [`pymmcore`](https://github.com/micro-manager/pymmcore) (python bindings
  for Micro-manager's C++ `CMMCore`). [`pymmcore_plus.CMMCorePlus`][pymmcore_plus.CMMCorePlus] (the main object in this library)
  aims to be a drop-in replacement for `pymmcore.CMMCore`, while adding a number
  of additional features including:

    - A multi-dimensional [acquisition engine][pymmcore_plus.CMMCorePlus.run_mda]
      implemented in pure python. (The existing acquisition engines in
      Micro-manager are written in Java and Clojure).
    - More flexible [event](guides/events.md) connections and callback handling.
    - Extended convenience APIs for working with core (which would be hard or
      impossible to implement in the `pymmcore` SWIG wrapper).
    - More pythonic APIs for various pymmcore objects (e.g. [`pymmcore_plus.Device`][],
      [`pymmcore_plus.Configuration`][]) and [constants](guides/constants.md).

- [`pymmcore-widgets`](../pymmcore-widgets/index.md) is a
    [Qt](https://www.qt.io)-based widget library built on
    `pymmcore-plus` that provides GUI elements for
    most of the device and acquisition functionality of `pymmcore`.  It
    allows users to build their own custom GUIs for Micro-manager.
- [`napari-micromanager`](../napari-micromanager/index.md)
    is a plugin for the [napari](https://napari.org/) image viewer that composes
    `pymmcore-plus` and `pymmcore-widgets` to provide a full GUI for
    Micro-manager that is integrated with the napari viewer.

!!! question "How is pymmcore-plus different than Pycro-Manager?"

    A common question about `pymmcore-plus` and related libraries is how it
    differs from [Pycro-Manager](https://github.com/micro-manager/pycro-manager),
    another python library written by Henry Pinkard for working with Micro-manager.
    
    The two projects are not mutually exclusive! They aim to support
    different use cases

    The primary difference is that Pycro-Manager controls Micro-manager
    via a ZMQ-based connection to a remote Java process in which the Micro-manager
    GUI is running (or a headless Java process if the GUI is not running). The
    Java process in turn communicates with the C++ core driving the hardware.

    `pymmcore-plus` aims to remove the need for a Java process by communicating
    directly with the C++ core (via the
    [`pymmcore`](https://github.com/micro-manager/pymmcore) library), and
    re-implementing any necessary event-based or GUI-based functionality in pure
    python or C.

    A major advantage of Pycro-Manager is that you get the entire Java-based
    micro-manager ecosystem, including the GUI and plugins. A potential disadvantage
    (depending on your needs), is that it requires a Java runtime environment and
    cross-process communication.
    
    If you are looking to control a microscope via python without any need for Java
    or interprocess communication, `pymmcore(-plus)` may help. Note however, that
    you will be sacrificing the MMStudio GUI! See `pymmcore-widgets` and
    `napari-micromanager`, and `pymmcore-gui` for ongoing efforts to implement a
    complete python-based GUI for Micro-manager.

    ![micro-manager ecosystem components](images/components.png){ loading=lazy }

## Getting started

- [Install](install.md) `pymmcore-plus` and the Micro-Manager device adapters.
- [First steps](../getting-started/first-steps.md): load a configuration, snap
  images, read and set properties, react to events.
- [Your first acquisition](../getting-started/first-acquisition.md): run
  multi-dimensional acquisitions.
- The [`CMMCorePlus` reference][pymmcore_plus.CMMCorePlus] lists every method of
  the core, marking what `pymmcore-plus` adds (:sparkles:) or overrides
  (:material-plus-thick:).

## Contributing

We welcome contributions to `pymmcore-plus` and related libraries.  Please see
[contributing](contributing.md) for more information.
