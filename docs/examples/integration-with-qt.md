# Qt Integration

`pymmcore-plus` is designed to integrate with Qt GUIs.  (For complete Qt applications
built on it, see [pymmcore-gui](../../pymmcore-gui/index.md), and the widgets in
[pymmcore-widgets](../../pymmcore-widgets/widgets/index.md).)  It accomplishes this in
two ways:

1. [`CMMCorePlus.run_mda`][pymmcore_plus.CMMCorePlus.run_mda] runs in a thread in
   order to not block the event loop.
2. The [`events`](../guides/events.md) objects (`core.events` and `core.mda.events`)
   use Qt signals instead of signals from the
   [psygnal](https://github.com/pyapp-kit/psygnal) library when a Qt application is
   running.  A Qt signal emitted in another thread is delivered in the main thread
   (to callbacks connected from the main thread), which keeps things from crashing
   when your callbacks update the GUI.

The examples on this page require qtpy, superqt and a Qt backend installed in the
environment (all of which come with `pip install "pymmcore-widgets[PyQt6]"`):

```bash
pip install qtpy superqt PyQt6  # or PySide6
```

## Create the QApplication first

Whether `CMMCorePlus` uses Qt signals or psygnal is decided once, when the core is
created.  It uses Qt signals if a `QApplication` exists at that moment, and psygnal
otherwise.  So **create the `QApplication` before the `CMMCorePlus`** (and that includes the first
call to `CMMCorePlus.instance()`, which is what creates the global core):

```python
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

app = QApplication([])
core = CMMCorePlus.instance()

print(type(core.events).__name__)  # QCoreSignaler
```

If the core comes first, `core.events` is a psygnal `CMMCoreSignaler`, and the
callbacks connected to `core.mda.events` (`frameReady`, `sequenceFinished`, etc...)
run in the acquisition thread.  Qt widgets may only be touched from the main thread,
so updating the GUI from one of those callbacks can crash the application, or make it
misbehave in less obvious ways.  (The events guide has more on
[which thread runs your callbacks](../guides/events.md#threads).)

You can also choose the backend with the `PYMM_SIGNALS_BACKEND` environment variable
(`qt`, `psygnal` or `auto`; see [Environment variables](../env_var.md)).
Importing `pymmcore_widgets` sets it to `qt` (unless you've set it yourself), so in a
GUI built from the widgets the order matters less.  But creating the application
first is a good habit.

## Avoiding blocking the Qt event loop

If you make a blocking call on the thread running the Qt event loop then your GUI will
become unresponsive.  The recommended way to avoid this is to use threads to call
blocking methods like [`snapImage`][pymmcore_plus.CMMCorePlus.snapImage] yourself, and
let pymmcore-plus handle the threading when you use
[`run_mda`][pymmcore_plus.CMMCorePlus.run_mda].

The simple application below consists of a counter that increments so long as the
event loop is not blocked, and two buttons that call the `snapImage` method (with a
5 second exposure).  One button calls it from a thread, and the counter continues; the
other blocks, and the counter stops.  Things to notice in the code below:

1. Create the `QApplication` before the core.
2. Use `CMMCorePlus.instance()` to create the core object.  This allows another
   script (or widget) in the same process to use the same object.
3. Use a thread for blocking operations like `snapImage`.

```python
import sys

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import create_worker

from pymmcore_plus import CMMCorePlus


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mmc = CMMCorePlus.instance()
        self.mmc.loadSystemConfiguration()
        self.mmc.setExposure(5000)  # 5 seconds

        self.counter = 0

        layout = QVBoxLayout()

        self.l = QLabel("Start")
        b_blocking = QPushButton("Snap blocking")
        b_threaded = QPushButton("Snap threaded")
        b_blocking.pressed.connect(self.snap_blocking)
        b_threaded.pressed.connect(self.snap_threaded)

        layout.addWidget(self.l)
        layout.addWidget(b_blocking)
        layout.addWidget(b_threaded)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show()

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._recurring_timer)
        self.timer.start()

    def _recurring_timer(self):
        self.counter += 1
        self.l.setText("Counter: %d" % self.counter)

    def snap_threaded(self):
        # alternatively you could use the python threading module
        # or directly use QThreads
        create_worker(
            self.mmc.snapImage,
            _start_thread=True,
        )

    def snap_blocking(self):
        self.mmc.snapImage()


app = QApplication(sys.argv)  # the app first...
window = MainWindow()  # ... then the core (created in MainWindow.__init__)
app.exec()
```

## Running an acquisition from a Qt application

[`run_mda`][pymmcore_plus.CMMCorePlus.run_mda] starts the acquisition in another
thread and returns immediately, so you can call it right before starting the event
loop (or from a button).  Because the `QApplication` exists before the core, the
`frameReady` callback below runs in the main thread, where it would be safe to update
a widget with the new image.  The STOP button cancels the acquisition:

```python title="examples/qt_integration.py"
--8<-- "examples/qt_integration.py"
```
