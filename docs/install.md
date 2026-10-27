# Micro-Manager Device Adapters

Just like the underlying [`pymmcore`](https://github.com/micro-manager/pymmcore) library,
`pymmcore-plus` relies on the device adapters and C++ core provided by
[mmCoreAndDevices](https://github.com/micro-manager/mmCoreAndDevices#mmcoreanddevices).
(The Python packages themselves are covered on the
[Installation](../getting-started/install.md) page.)

## Installing Micro-Manager device adapters

The device adapters can be installed in two ways:

1. **Use the `mmcore` command line tool**

    `pymmcore-plus` provides a quick way to install the latest compatible version
    of Micro-Manager:

    ```bash
    mmcore install
    ```

    This will download the most recent nightly build of Micro-Manager that matches
    your version of `pymmcore` and, by default, place it in a `pymmcore-plus/mm`
    folder in the user's data directory:

    | OS      | Path |
    | ------- | ---- |
    | Windows | `C:\Users\UserName\AppData\Local\pymmcore-plus\pymmcore-plus\mm` |
    | macOS   | `~/Library/Application Support/pymmcore-plus/mm` |
    | Linux   | `~/.local/share/pymmcore-plus/mm` |

    If you would like to modify the location of the installation, or the release
    of Micro-Manager to install, you can use the `--dest` and `--release` flags
    respectively.

    For more information on the `install` command, run:

    ```bash
    mmcore install --help
    ```

    To explore all the `mmcore` command line tool functionalities, run
    `mmcore --help` (or see the [CLI reference](cli.md)).

2. **Download manually from micro-manager.org**

    Go to the [Micro-Manager nightly
    builds](https://micro-manager.org/Micro-Manager_Nightly_Builds) page and
    download a build for your operating system whose device interface version
    matches your `pymmcore` (see
    [below](#understanding-device-interface-versions)).  This is *not*
    necessarily the latest release.

!!! warning "Apple Silicon and Linux"

    Micro-Manager only publishes nightly builds for Windows and Intel macOS.  On
    Linux, and on macOS with an Apple Silicon (M1, M2, ...) processor,
    `mmcore install` prints `Unsupported platform/architecture for nightly build`
    and installs just the *test* adapters (`DemoCamera`, `Utilities`,
    `SequenceTester` and `NotificationTester`) from
    [mm-test-adapters](https://github.com/micro-manager/mm-test-adapters).  That's
    enough for the demo configuration used throughout these docs, but to
    control real hardware you will need to build the adapters you need
    (see [Building device adapters](#building-device-adapters) below).

!!! danger "Critical"

    The *device interface version* MUST match between `pymmcore` and the
    Micro-Manager device adapters. See [below](#understanding-device-interface-versions).

## Showing the current installation

To see which Micro-Manager installations `pymmcore-plus` has found, and which one
it is using, run:

```shell
mmcore list
```

The output looks something like this (the active installation is marked with ➤):

```console
Required pymmcore device interface version: 75

📁 ~/Library/Application Support/pymmcore-plus/mm
   ➤ Micro-Manager-75.20260226 (DIV 75) (active)
   • Micro-Manager-74.20260129 (DIV 74) (incompatible)
```

From Python, you can use [`find_micromanager`][pymmcore_plus.find_micromanager]:

```shell
python -c "from pymmcore_plus import find_micromanager; print(find_micromanager())"
```

## Setting the active installation

When you create a [`CMMCorePlus`][pymmcore_plus.CMMCorePlus], `pymmcore-plus`
looks for device adapters in the following places, and uses the first one whose
device interface version matches `pymmcore`:

1. The `MICROMANAGER_PATH` environment variable (always used, if set).
2. A path previously selected with `mmcore use` (see below).  If it's no longer
   compatible, it is forgotten (with a warning).
3. The `mmcore install` folder in the user data directory (see the table above).
   If there are several compatible installations there, the last one in
   alphabetical order is used.
4. The [`mm-test-adapters`](https://pypi.org/project/mm-test-adapters/) Python
   package, if it is installed.
5. A `Micro-Manager*` folder in the default Micro-Manager install location:
   `C:\Program Files\` on Windows, `/Applications/` on macOS, and
   `/usr/local/lib/` on Linux.

So if you already have Micro-Manager installed in the default location, and
`mmcore list` says that it is compatible, it will be found automatically (unless
one of the earlier locations also has a compatible installation).  If
`mmcore list` says that it's incompatible, run `mmcore install` to get a
compatible set of adapters.

!!! tip "Using the Micro-Manager app too?"

    That's fine, but `pymmcore-plus` doesn't connect to a running Micro-Manager
    (it loads the device adapters itself).  Most devices can only be opened by one
    program at a time, so close Micro-Manager before you load the same hardware
    configuration in Python (and vice versa).

To override the device adapter search path for a single session (or script), set
the `MICROMANAGER_PATH` environment variable:

```shell
export MICROMANAGER_PATH=/path/to/installation
```

(For a single core object, you can also pass the folder directly:
`CMMCorePlus(mm_path="/path/to/installation")`.)

If you want to permanently set the Micro-Manager installation path that
`pymmcore-plus` uses, you can use the `mmcore use` command:

```shell
mmcore use <some path or pattern>
```

... where `<some path or pattern>` is either a path to an existing directory
(containing Micro-Manager device adapters) or a pattern to match against
directories returned by [`find_micromanager`][pymmcore_plus.find_micromanager].

Alternatively, you can use the
[`use_micromanager`][pymmcore_plus.use_micromanager] function, passing *either*
a path to an existing directory, or a pattern to match against directories
returned by [`find_micromanager`][pymmcore_plus.find_micromanager]:

```shell
python -c "from pymmcore_plus import use_micromanager; use_micromanager(path=..., pattern=...)"
```

## Building device adapters

On Linux and Apple Silicon there are no pre-built Micro-Manager adapters beyond
the test devices, so you will need to build the C++ core and device adapters
yourself from
[mmCoreAndDevices](https://github.com/micro-manager/mmCoreAndDevices#mmcoreanddevices).
To do that, follow the [build
instructions](https://github.com/micro-manager/micro-manager/blob/main/doc/how-to-build.md#building-on-unix)
in the micro-manager repo, then point `pymmcore-plus` at the folder with
`mmcore use`.

On macOS and Linux, `mmcore build-dev` can also clone the repository and build a
few adapters for you (`DemoCamera`, `Utilities` and `SequenceTester` by default,
or the names you pass it).  Not all adapters will build this way, and you'll need
the build tools described in the instructions above.  Run
`mmcore build-dev --help` for the options.

## Understanding device interface versions

Micro-Manager's C++ layer (called MMCore) controls devices via adapters that are
compiled into platform-specific shared libraries.  These libraries are always
compiled to work with a *specific* "device interface version" expected by the
MMCore object itself.  If you try to load a device adapter with a device
interface version that does not match the version expected by the core, then you
will get an error.

[pymmcore](https://github.com/micro-manager/pymmcore) is a library that wraps
the C++ code and makes it available to Python.  It has a 5-number version string
that looks something like `12.5.1.75.0`.  The first three parts (here: `12.5.1`)
represent the version of the MMCore library.  The next number (here: `75`) *is
the device interface version that pymmcore expects*.  (The last number is a
pymmcore-specific build number).  To query version information of your installed
libraries you can run:

```bash
mmcore --version
```

!!! danger "Critical"

    **You *must* use device adapter libraries that were compiled for the same device
    interface version as your version of pymmcore.**

    By default, when you run `mmcore install`, it will pick the latest compatible
    version to install. However, you can also do this explicitly.  For example,
    with an older pymmcore that expects device interface version `74`, you could
    explicitly install the last compatible device adapters listed on the table
    below with `mmcore install` as follows:

    ```sh
    mmcore install -r 20260225
    ```

Here is a list of the latest device interface numbers, the date of the first
nightly build where they were available, the last nightly build date to support
that version, and the commit in
[mmCoreAndDevices](https://github.com/micro-manager/mmCoreAndDevices) that
bumped the version.

|Version|Release Date|Last Release|Commit|
|-------|----|-----|------|
|75|20260226|        |[3c6312ac5](https://github.com/micro-manager/mmCoreAndDevices/commit/3c6312ac5)|
|74|20250815|20260225|[7e9f2f214](https://github.com/micro-manager/mmCoreAndDevices/commit/7e9f2f214)|
|73|20250318|20250814|[55863b2d8](https://github.com/micro-manager/mmCoreAndDevices/commit/55863b2d8)|
|72|20250318|20250318|[b8de737b2](https://github.com/micro-manager/mmCoreAndDevices/commit/b8de737b2)|
|71|20221031|20250310|[7ba63fb8f](https://github.com/micro-manager/mmCoreAndDevices/commit/7ba63fb8f)|
|70|20210219|20221030|[8687ddb51](https://github.com/micro-manager/mmCoreAndDevices/commit/8687ddb51)|
|69|20180712||[1a9938168](https://github.com/micro-manager/mmCoreAndDevices/commit/1a9938168)|
|68|20171107||[285a9fbb2](https://github.com/micro-manager/mmCoreAndDevices/commit/285a9fbb2)|
|67|20160609||[2cafb3481](https://github.com/micro-manager/mmCoreAndDevices/commit/2cafb3481)|

??? information "Older versions"

    |Version|Release Date|Commit|
    |-------|----|------|
    |66|20160608|[6378720c9](https://github.com/micro-manager/mmCoreAndDevices/commit/6378720c9)|
    |65|20150528|[b98858d3b](https://github.com/micro-manager/mmCoreAndDevices/commit/b98858d3b)|
    |64|20150515|[6fdcdc274](https://github.com/micro-manager/mmCoreAndDevices/commit/6fdcdc274)|
    |63|20150505|[ae4ced454](https://github.com/micro-manager/mmCoreAndDevices/commit/ae4ced454)|
    |62|20150501|[38cfde8ef](https://github.com/micro-manager/mmCoreAndDevices/commit/38cfde8ef)|
    |61|20140801|[aac034a5c](https://github.com/micro-manager/mmCoreAndDevices/commit/aac034a5c)|
    |60|20140618|[cff69f1c2](https://github.com/micro-manager/mmCoreAndDevices/commit/cff69f1c2)|
    |59|20140515|[1a3c3c884](https://github.com/micro-manager/mmCoreAndDevices/commit/1a3c3c884)|
    |58|20140514|[b3781c0a9](https://github.com/micro-manager/mmCoreAndDevices/commit/b3781c0a9)|
    |57|20140125|[97beb0f6c](https://github.com/micro-manager/mmCoreAndDevices/commit/97beb0f6c)|
    |56|20140120|[bbf1b852c](https://github.com/micro-manager/mmCoreAndDevices/commit/bbf1b852c)|
    |55|20131221|[d9d939aed](https://github.com/micro-manager/mmCoreAndDevices/commit/d9d939aed)|
    |54|20131022|[0058a1202](https://github.com/micro-manager/mmCoreAndDevices/commit/0058a1202)|
    |53|20121108|[34329bb10](https://github.com/micro-manager/mmCoreAndDevices/commit/34329bb10)|
    |52|20120925|[feeeff5d0](https://github.com/micro-manager/mmCoreAndDevices/commit/feeeff5d0)|
    |51|20120117|[c62cd71df](https://github.com/micro-manager/mmCoreAndDevices/commit/c62cd71df)|
    |50|20120117|[121dea472](https://github.com/micro-manager/mmCoreAndDevices/commit/121dea472)|
    |49|20111026|[0f999b4f7](https://github.com/micro-manager/mmCoreAndDevices/commit/0f999b4f7)|
    |48|20111010|[5407292c4](https://github.com/micro-manager/mmCoreAndDevices/commit/5407292c4)|
    |47|20110916|[de02aa524](https://github.com/micro-manager/mmCoreAndDevices/commit/de02aa524)|
    |46|20110915|[f886a5a60](https://github.com/micro-manager/mmCoreAndDevices/commit/f886a5a60)|
    |45|20110722|[3de97a552](https://github.com/micro-manager/mmCoreAndDevices/commit/3de97a552)|
    |44|20110721|[adffbed3c](https://github.com/micro-manager/mmCoreAndDevices/commit/adffbed3c)|
    |43|20110721|[f1fa3260c](https://github.com/micro-manager/mmCoreAndDevices/commit/f1fa3260c)|
    |42|20110720|[70d420b79](https://github.com/micro-manager/mmCoreAndDevices/commit/70d420b79)|
    |41|20110626|[6f1e9e3c7](https://github.com/micro-manager/mmCoreAndDevices/commit/6f1e9e3c7)|
    |40|20110526|[c9c4f901b](https://github.com/micro-manager/mmCoreAndDevices/commit/c9c4f901b)|
    |39|20110411|[d6cf30e11](https://github.com/micro-manager/mmCoreAndDevices/commit/d6cf30e11)|
    |38|20110324|[5fb856c6d](https://github.com/micro-manager/mmCoreAndDevices/commit/5fb856c6d)|
    |39|20110322|[aca92c283](https://github.com/micro-manager/mmCoreAndDevices/commit/aca92c283)|
    |38|20101224|[3327c6083](https://github.com/micro-manager/mmCoreAndDevices/commit/3327c6083)|
    |37|20101221|[63e284ccf](https://github.com/micro-manager/mmCoreAndDevices/commit/63e284ccf)|
    |36|20100920|[7b180c4ef](https://github.com/micro-manager/mmCoreAndDevices/commit/7b180c4ef)|
    |35|20100823|[41603ae0c](https://github.com/micro-manager/mmCoreAndDevices/commit/41603ae0c)|
    |34|20100202|[5bd9a38d5](https://github.com/micro-manager/mmCoreAndDevices/commit/5bd9a38d5)|
    |28|20080911|[ecdc3ffe9](https://github.com/micro-manager/mmCoreAndDevices/commit/ecdc3ffe9)|
    |27|20080806|[644297085](https://github.com/micro-manager/mmCoreAndDevices/commit/644297085)|
    |26|20080604|[99fd3cd80](https://github.com/micro-manager/mmCoreAndDevices/commit/99fd3cd80)|
    |16|20070412|[38ebafde1](https://github.com/micro-manager/mmCoreAndDevices/commit/38ebafde1)|
    |15|20070405|[18ec4b48b](https://github.com/micro-manager/mmCoreAndDevices/commit/18ec4b48b)|
    |14|20070227|[3b69e7670](https://github.com/micro-manager/mmCoreAndDevices/commit/3b69e7670)|
