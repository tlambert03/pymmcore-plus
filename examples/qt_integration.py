"""
An example of integrating a MMCore object into an event loop.

This example requires qtpy and a Qt backend installed in the env:
```
pip install qtpy PyQt6  # or PySide6
```
"""

import numpy as np
from qtpy.QtWidgets import QApplication, QPushButton
from useq import MDAEvent, MDASequence

from pymmcore_plus import CMMCorePlus

# create the QApplication *before* the core, so that the core uses Qt signals
app = QApplication([])
mmcore = CMMCorePlus.instance()

# button for early stopping
stop = QPushButton("STOP")


def stop_clicked():
    mmcore.mda.cancel()
    app.quit()


stop.clicked.connect(stop_clicked)
stop.show()


@mmcore.mda.events.frameReady.connect
def on_frame(image: np.ndarray, event: MDAEvent):
    # with Qt signals, this runs in the main thread (not the acquisition thread),
    # so it's safe to update widgets from here
    print(
        f"received frame: {image.shape}, {image.dtype} "
        f"@ index {event.index}, z={event.z_pos}"
    )


@mmcore.events.propertyChanged.connect
def prop_changed(device, prop, value):
    print(f"{device}.{prop} changed to {value!r}")


# setup some callbacks
mmcore.events.systemConfigurationLoaded.connect(lambda: print("config loaded!"))
mmcore.mda.events.sequenceFinished.connect(app.quit)

# load config and start an experiment
mmcore.loadSystemConfiguration()

# see https://github.com/pymmcore-plus/useq-schema
x, y = mmcore.getXYPosition()
sequence = MDASequence(
    channels=["DAPI", {"config": "FITC", "exposure": 50}],
    time_plan={"interval": 1.5, "loops": 5},
    # a relative z plan is relative to the stage position, so give it the current one
    stage_positions=[(x, y, mmcore.getZPosition())],
    z_plan={"range": 4, "step": 0.5},
    axis_order="tpcz",
)

mmcore.run_mda(sequence)  # runs in another thread, and returns immediately

# start the qt event loop
app.exec()
