# Logging

By default, pymmcore-plus logs to the console at the `WARNING` level and to a
logfile in the pymmcore-plus application data directory at the `DEBUG` level.
The logfile is named `pymmcore-plus.log` and is rotated at 40MB, with a maximum
retention of 20 logfiles.

## Customizing logging

The [`pymmcore_plus.configure_logging`][] function allows you to customize the
log level, logfile name, and logfile rotation settings.  For example, to see
everything that pymmcore-plus is doing in the console:

```python
from pymmcore_plus import configure_logging

configure_logging(stderr_level="DEBUG")
```

You may also configure logging using the following environment variables
(set them before importing `pymmcore_plus`):

| Variable       | Default                                                | Description           |
| -------------- | ------------------------------------------------------ | --------------------- |
| PYMM_LOG_LEVEL | `WARNING`                                              | The console log level (e.g. `INFO` or `DEBUG`). |
| PYMM_LOG_FILE  | `pymmcore-plus.log` in the pymmcore-plus log directory | The logfile location. Set to `0`, `false`, `no`, or `none` to disable logging to a file. |
| PYMM_LOG_RICH  | `0` (disabled)                                         | Use [rich](https://rich.readthedocs.io/) for stderr logging. Set to `1`, `true`, or `yes` to enable. Note: adds some formatting overhead ([#449](https://github.com/pymmcore-plus/pymmcore-plus/issues/449)). |

(See [environment variables](../env_var.md) for the full list.)

!!! tip "pymmcore-plus log directory"

    The application data directory is platform-dependent. Here are the
    log folders for each supported platform:

    | OS     |  Path  |
    | ------ | ------ |
    | macOS  | ~/Library/Application Support/pymmcore-plus/logs |
    | Linux  | ~/.local/share/pymmcore-plus/logs |
    | Win    | C:\Users\username\AppData\Local\pymmcore-plus\pymmcore-plus\logs |

    You can also use `mmcore logs --reveal` to open the log directory in your
    file manager.

Note that both pymmcore-plus and the underlying CMMCore object will write to the log
file. By default, [CMMCorePlus][pymmcore_plus.CMMCorePlus] will call `setPrimaryLogFile()`
with the location of the pymmcore-plus logfile upon instantiation.  The C++ core's
own logging can be controlled with the methods in the
[*Logging & errors*][cmmcoreplus-logging-errors] section of `CMMCorePlus` (e.g.
[`enableDebugLog`][pymmcore_plus.CMMCorePlus.enableDebugLog] and
[`setPrimaryLogLevel`][pymmcore_plus.CMMCorePlus.setPrimaryLogLevel]).

## Managing logs with the CLI

The `mmcore` CLI provides a `logs` subcommand for managing logs.

--8<-- "docs/_generated/cli_logs.md"

A particularly useful command is `mmcore logs --tail`, which will continually
stream the current logfile to the console. This can be started in another
process and left running to monitor an experiment in progress.

To delete all logfiles, use `mmcore logs --clear`.
