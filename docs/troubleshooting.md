# Troubleshooting

## Micro-Manager directory not found

```sh
pymmcore-plus - ERROR - (_discovery.py:256) Could not find a compatible Micro-Manager installation for the device interface required by pymmcore 75.

Discovered installations:

Please run 'mmcore install'.
```

... usually followed, when you call `loadSystemConfiguration()`, by:

```sh
FileNotFoundError: Path does not exist: MMConfig_demo.cfg
```

If you tried to create a [`pymmcore_plus.CMMCorePlus`][pymmcore_plus.CMMCorePlus]
instance and got an error similar to the one above, it means that pymmcore-plus
was unable to find a Micro-Manager installation on your system whose device
interface version matches your version of `pymmcore`.  Please run
`mmcore install` to install the latest compatible version of Micro-Manager.  You
can run `mmcore list` to see which installations were found (and which of them
are incompatible).

See the [installation](install.md#installing-micro-manager-device-adapters)
section for more details.

## Incompatible device interface version

```sh
OSError: Line 7: Device,DHub,DemoCamera,DHub
Failed to load device adapter "DemoCamera" from "/Users/user/Library/Application Support/pymmcore-plus/mm/Micro-Manager-74.20260129/libmmgr_dal_DemoCamera" [ Incompatible device interface version (MMCore requires 75; device adapter has 74) ]
```

If you create a [`pymmcore_plus.CMMCorePlus`][pymmcore_plus.CMMCorePlus] instance and
you get an error similar to the one above when trying to load a Micro-Manager
configuration file, the device adapters that pymmcore-plus is using were built
for a different device interface version than your `pymmcore`.  This usually
means that `MICROMANAGER_PATH` (or the `mm_path` you passed to `CMMCorePlus`)
points to an older (or newer) installation.  Either
point it at a compatible installation, or **update** your Micro-Manager device
adapters (for example by running: `mmcore install`).

See [understanding device interface
versions](install.md#understanding-device-interface-versions) for more details.

## Slow performance

If you are experiencing slow performance with pymmcore-plus, you can profile
your code to identify bottlenecks.  See the [profiling](profiling.md) section
for more details. If you identify a specific issue, or have a question regarding
the interpretation of the profiling results, please
[open an issue](https://github.com/pymmcore-plus/pymmcore-plus/issues/new) and
attach the profiling results if possible.

## Something else?

Turning up the [log level](guides/logging.md) (`PYMM_LOG_LEVEL=DEBUG`) often
shows what pymmcore-plus was doing when things went wrong, and `mmcore logs`
shows the log file.  If you're still stuck, please
[open an issue](https://github.com/pymmcore-plus/pymmcore-plus/issues/new) and
include the output of `mmcore info`.
