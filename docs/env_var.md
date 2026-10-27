# Environment Variables

The following environment variables may be used to configure pymmcore-plus globally.

<small>*Unless noted otherwise, boolean variables can be set to `1`, `0`, `True`, or `False` (case insensitive).*</small>

| <div style="width:140px">Variable</div>    | Description     | Default |
|--------------------------------------------|-----------------| ------- |
| **`PYMM_DEBUG_LOG`**  | Call `enableDebugLog(True)` when creating a `CMMCorePlus`.  |      |
| **`PYMM_STDERR_LOG`**  | Call `enableStderrLog(True)` when creating a `CMMCorePlus`.  |      |
| **`PYMM_BUFFER_SIZE_MB`**  | Circular buffer memory footprint in MB.  |  MMCore's default (250 MB)   |
| **`PYMM_STRICT_INIT_CHECKS`**  | Enable/disable strict initialization checks  |  Enabled    |
| **`PYMM_PARALLEL_INIT`**  | Enable/disable parallel device initialization  |  Enabled    |
| **`PYMM_LOG_LEVEL`**                       | pymmcore-plus [logging](./guides/logging.md) level for the console.  | `'WARNING'`    |
| **`PYMM_LOG_FILE`**   | Logfile location.  Set to `0`, `false`, `no` or `none` to disable logging to a file. | `pymmcore-plus.log` in the pymmcore-plus [log directory](./guides/logging.md#customizing-logging) |
| **`PYMM_LOG_RICH`**   | Use [rich](https://rich.readthedocs.io/) for stderr logging (`1`, `true` or `yes`). Adds some formatting overhead ([#449](https://github.com/pymmcore-plus/pymmcore-plus/issues/449)). | `"0"` (disabled) |
| **`MICROMANAGER_PATH`**   | Override location of Micro-Manager directory (with device adapters) | Found automatically (see the [search order](./install.md#setting-the-active-installation))   |
| **`PYMM_SIGNALS_BACKEND`** | The event backend to use. Must be one of `'qt'`, `'psygnal'`, or `'auto'`  | `auto` (Qt if a `QApplication` exists when `CMMCorePlus` is created, otherwise psygnal) |
| **`PYMM_DISABLE_IPYTHON_COMPLETIONS`**  | Set to `1` to disable [Tab autocompletion for IPython](./guides/ipython_completion.md)  | `"0"`  (enabled) |
| **`UNICORE_SEQUENCE_BUFFER_MB`**  | Size of the sequence buffer used by [`UniMMCore`](./guides/unicore.md) for Python cameras, in MB.  | 1024 MB (250 MB on CI) |
