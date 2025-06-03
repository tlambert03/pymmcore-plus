# Examples

This page provides practical examples demonstrating various features and use cases of pymmcore-plus. All examples are available in the [examples/](https://github.com/pymmcore-plus/pymmcore-plus/tree/main/examples) directory of the repository.

## Basic MDA Examples

### Simple MDA Acquisition

A basic multi-dimensional acquisition with time-lapse and channels:

```python
# examples/run_mda.py
from useq import MDASequence
from pymmcore_plus import CMMCorePlus

# Create core instance and load configuration
core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# Define sequence with multiple dimensions
sequence = MDASequence(
    time_plan={"interval": 2, "loops": 5},
    channels=["DAPI", "FITC"],
    z_plan={"range": 4, "step": 0.5},
    axis_order="tpcz"
)

# Run the acquisition
core.run_mda(sequence)
```

### OME-TIFF Output

Save MDA data directly to OME-TIFF format:

```python
# examples/ome_tiff_mda.py
import numpy as np
from useq import MDASequence, MDAEvent
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import OMETiffWriter
from pymmcore_plus.mda import mda_listeners_connected

core = CMMCorePlus.instance()

# Create sequence
sequence = MDASequence(
    time_plan={"interval": 1, "loops": 3},
    channels=["DAPI", "FITC"],
    z_plan={"range": 5, "step": 1},
)

# Use OME-TIFF writer
writer = OMETiffWriter("acquisition.ome.tiff")
with mda_listeners_connected(writer):
    core.run_mda(sequence)

print("Data saved to acquisition.ome.tiff")
```

### OME-Zarr Output

For large datasets, use the Zarr format:

```python
# examples/zarr_mda.py
from useq import MDASequence
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import OMEZarrWriter
from pymmcore_plus.mda import mda_listeners_connected

core = CMMCorePlus.instance()

# Large acquisition sequence
sequence = MDASequence(
    time_plan={"interval": 30, "loops": 100},
    channels=["DAPI", "FITC", "Cy5"],
    z_plan={"range": 10, "step": 0.5},
    stage_positions=[(i*100, j*100) for i in range(5) for j in range(5)]
)

# Use Zarr writer for efficient large data storage
writer = OMEZarrWriter("large_acquisition.zarr", overwrite=True)
with mda_listeners_connected(writer):
    core.run_mda(sequence)

print("Large dataset saved to large_acquisition.zarr")
```

### Image Sequence Output

Save each frame as individual files:

```python
# examples/img_sequence_mda.py
from useq import MDASequence, MDAEvent
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import ImageSequenceWriter
from pymmcore_plus.mda import mda_listeners_connected

core = CMMCorePlus.instance()

sequence = MDASequence(
    time_plan={"interval": 5, "loops": 10},
    channels=["DAPI", "FITC"],
    z_plan={"range": 8, "step": 1}
)

# Save as individual TIFF files
writer = ImageSequenceWriter(
    "image_sequence_output",
    extension=".tiff",
    prefix="frame_",
    include_frame_count=True
)

with mda_listeners_connected(writer):
    core.run_mda(sequence)

print("Image sequence saved to image_sequence_output/")
```

### TensorStore Integration

Use TensorStore for cloud-compatible storage:

```python
# examples/tensorstore_mda.py
from useq import MDASequence
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import TensorStoreHandler
from pymmcore_plus.mda import mda_listeners_connected

core = CMMCorePlus.instance()

sequence = MDASequence(
    time_plan={"interval": 10, "loops": 20},
    channels=["DAPI", "FITC"],
    z_plan={"range": 6, "step": 0.5}
)

# TensorStore with Zarr driver
writer = TensorStoreHandler(
    "tensorstore_acquisition.zarr",
    driver="zarr",
    kvstore={"driver": "file"}
)

with mda_listeners_connected(writer):
    core.run_mda(sequence)

print("Data saved with TensorStore")
```

## Event System Examples

### Event-Driven Acquisition

Respond to hardware events and dynamic imaging conditions:

```python
# examples/event_driven_acquisition.py
import numpy as np
from useq import MDASequence, MDAEvent
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus.instance()

# Connect to various events
@core.mda.events.sequenceStarted.connect
def on_sequence_start(sequence: MDASequence):
    print(f"Starting acquisition: {len(list(sequence))} total events")

@core.mda.events.frameReady.connect
def on_frame_ready(image: np.ndarray, event: MDAEvent):
    # Real-time image analysis
    mean_intensity = np.mean(image)
    print(f"Frame {event.index}: {image.shape}, mean intensity: {mean_intensity:.1f}")
    
    # Example: adaptive imaging based on intensity
    if mean_intensity < 100:
        print("Low intensity detected - might need longer exposure")

@core.mda.events.sequenceFinished.connect
def on_sequence_finished(sequence: MDASequence):
    print("Acquisition completed successfully")

@core.mda.events.sequencePauseToggled.connect
def on_pause_toggled(paused: bool):
    print(f"Acquisition {'paused' if paused else 'resumed'}")

# Define and run sequence
sequence = MDASequence(
    time_plan={"interval": 3, "loops": 10},
    channels=["DAPI", "FITC"],
    z_plan={"range": 5, "step": 1}
)

core.run_mda(sequence)
```

### Properties and State Events

Monitor device property changes and system state:

```python
# examples/properties_and_state_events.py
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# Monitor property changes
@core.events.propertyChanged.connect
def on_property_changed(device: str, property: str, value: str):
    print(f"Property changed: {device}.{property} = {value}")

# Monitor configuration changes
@core.events.configSet.connect
def on_config_changed(group: str, config: str):
    print(f"Configuration changed: {group} -> {config}")

# Monitor stage position changes
@core.events.xYStagePositionChanged.connect
def on_xy_position_changed(device: str, x: float, y: float):
    print(f"Stage moved: {device} -> ({x:.2f}, {y:.2f})")

@core.events.stagePositionChanged.connect
def on_z_position_changed(device: str, position: float):
    print(f"Z position changed: {device} -> {position:.2f}")

# Test property changes
if core.getLoadedDevices():
    # Change some properties to trigger events
    stage_device = core.getXYStageDevice()
    if stage_device:
        current_x, current_y = core.getXYPosition()
        core.setXYPosition(current_x + 10, current_y + 10)
        
    # Change configuration if available
    config_groups = core.getAvailableConfigGroups()
    if config_groups:
        group = config_groups[0]
        configs = core.getAvailableConfigs(group)
        if len(configs) > 1:
            core.setConfig(group, configs[0])

print("Property monitoring active. Make changes to see events.")
```

## Integration Examples

### Napari Integration

Real-time visualization with napari:

```python
# examples/napari.py
import napari
import numpy as np
from useq import MDASequence, MDAEvent
from pymmcore_plus import CMMCorePlus

# Start napari viewer
viewer = napari.Viewer()

core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# Layer to display images
image_layer = None

@core.mda.events.frameReady.connect
def display_in_napari(image: np.ndarray, event: MDAEvent):
    global image_layer
    
    # Add or update layer
    if image_layer is None:
        image_layer = viewer.add_image(
            image, 
            name=f"Channel {event.channel.config}",
            metadata=event.model_dump()
        )
    else:
        image_layer.data = image
        image_layer.metadata = event.model_dump()
    
    # Update layer name with current info
    channel = event.channel.config if event.channel else "Unknown"
    t = event.index.get('t', 0)
    z = event.index.get('z', 0)
    image_layer.name = f"{channel} t={t} z={z}"

# Define sequence
sequence = MDASequence(
    time_plan={"interval": 2, "loops": 5},
    channels=["DAPI", "FITC"],
    z_plan={"range": 6, "step": 1}
)

# Run acquisition with napari display
core.run_mda(sequence)

# Keep napari open
napari.run()
```

### Qt Integration

Integrate with Qt applications:

```python
# examples/qt_integration.py
import sys
from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from qtpy.QtCore import QThread, Signal
import numpy as np
from useq import MDASequence, MDAEvent
from pymmcore_plus import CMMCorePlus

class MDAThread(QThread):
    frameReceived = Signal(np.ndarray, object)  # image, event
    sequenceFinished = Signal()
    
    def __init__(self, sequence):
        super().__init__()
        self.sequence = sequence
        self.core = CMMCorePlus.instance()
        
    def run(self):
        @self.core.mda.events.frameReady.connect
        def on_frame(image, event):
            self.frameReceived.emit(image, event)
            
        @self.core.mda.events.sequenceFinished.connect
        def on_finished(seq):
            self.sequenceFinished.emit()
            
        self.core.run_mda(self.sequence)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyMMCore-Plus Qt Integration")
        
        # UI setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.status_label = QLabel("Ready")
        self.start_button = QPushButton("Start MDA")
        self.frame_info_label = QLabel("No frames acquired")
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.frame_info_label)
        
        # Connect signals
        self.start_button.clicked.connect(self.start_mda)
        
        # Initialize core
        self.core = CMMCorePlus.instance()
        
    def start_mda(self):
        sequence = MDASequence(
            time_plan={"interval": 1, "loops": 5},
            channels=["DAPI", "FITC"],
            z_plan={"range": 4, "step": 1}
        )
        
        self.mda_thread = MDAThread(sequence)
        self.mda_thread.frameReceived.connect(self.on_frame_received)
        self.mda_thread.sequenceFinished.connect(self.on_sequence_finished)
        
        self.status_label.setText("Acquisition running...")
        self.start_button.setEnabled(False)
        self.mda_thread.start()
        
    def on_frame_received(self, image, event):
        channel = event.channel.config if event.channel else "Unknown"
        info = f"Frame: {image.shape}, Channel: {channel}, Index: {event.index}"
        self.frame_info_label.setText(info)
        
    def on_sequence_finished(self):
        self.status_label.setText("Acquisition complete")
        self.start_button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
```

## Advanced Examples

### Context Manager Usage

Use pymmcore-plus as a context manager for automatic cleanup:

```python
# examples/set_as_context.py
from pymmcore_plus import CMMCorePlus
from useq import MDASequence

# Context manager ensures proper cleanup
with CMMCorePlus.instance() as core:
    # Load configuration
    core.loadSystemConfiguration()
    
    # Set initial state
    original_exposure = core.getExposure()
    
    try:
        # Run acquisition with modified settings
        core.setExposure(50)
        
        sequence = MDASequence(
            time_plan={"interval": 1, "loops": 3},
            channels=["DAPI", "FITC"]
        )
        
        core.run_mda(sequence)
        
    finally:
        # Restore original state
        core.setExposure(original_exposure)
        print(f"Restored exposure to {original_exposure}")

# Core is automatically cleaned up when exiting context
```

### Pycro API Compatibility

Use micro-manager's pycro API syntax:

```python
# examples/pycro-api.py
from pymmcore_plus import CMMCorePlus

# Enable pycro API compatibility
core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# Use familiar micro-manager syntax
devices = core.getLoadedDevices()
print(f"Loaded devices: {devices}")

# Camera operations
if core.getCameraDevice():
    exposure = core.getExposure()
    print(f"Current exposure: {exposure} ms")
    
    # Snap image
    core.snapImage()
    image = core.getImage()
    print(f"Snapped image: {image.shape}")

# Stage operations
if core.getXYStageDevice():
    x, y = core.getXYPosition()
    print(f"Current XY position: ({x:.2f}, {y:.2f})")
    
    # Move stage
    core.setXYPosition(x + 10, y + 10)
    new_x, new_y = core.getXYPosition()
    print(f"New XY position: ({new_x:.2f}, {new_y:.2f})")

# Configuration management
config_groups = core.getAvailableConfigGroups()
for group in config_groups:
    current_config = core.getCurrentConfig(group)
    available_configs = core.getAvailableConfigs(group)
    print(f"Group '{group}': current='{current_config}', available={available_configs}")
```

### Universal Core (Unicore)

Use unicore for device simulation and testing:

```python
# examples/unicore.py
from pymmcore_plus import CMMCorePlus

# Create core instance
core = CMMCorePlus.instance()

# Load demo configuration (no real hardware needed)
try:
    core.loadSystemConfiguration("MMConfig_demo.cfg")
except:
    # If demo config not available, create minimal setup
    core.loadDevice("Camera", "DemoCamera", "DCam")
    core.loadDevice("XYStage", "DemoCamera", "DXYStage") 
    core.loadDevice("ZStage", "DemoCamera", "DStage")
    core.initializeAllDevices()
    
    # Set as default devices
    core.setCameraDevice("Camera")
    core.setXYStageDevice("XYStage")
    core.setFocusDevice("ZStage")

# Now use the core normally
print(f"Camera device: {core.getCameraDevice()}")
print(f"XY Stage device: {core.getXYStageDevice()}")

# Test basic operations
core.snapImage()
image = core.getImage()
print(f"Demo image captured: {image.shape}")

# Test stage movement
if core.getXYStageDevice():
    core.setXYPosition(100, 200)
    x, y = core.getXYPosition()
    print(f"Stage position: ({x}, {y})")

print("Unicore demo completed successfully!")
```

## Running the Examples

All examples can be run directly from the command line:

```bash
# Navigate to examples directory
cd examples/

# Run any example
python run_mda.py
python napari.py
python qt_integration.py
```

Some examples require additional dependencies:

```bash
# For napari integration
pip install napari[all]

# For Qt integration  
pip install qtpy PyQt5  # or PyQt6, PySide2, PySide6

# For TensorStore support
pip install tensorstore
```

## Tips for Using Examples

1. **Start Simple**: Begin with `run_mda.py` to understand basic MDA usage
2. **Hardware Requirements**: Most examples work with demo configurations
3. **Modify Parameters**: Adjust timing, exposure, and dimensions for your needs
4. **Error Handling**: Add try/catch blocks for production use
5. **Performance**: Use appropriate data formats (Zarr for large datasets)
6. **Integration**: Combine multiple examples for complex workflows

These examples provide a comprehensive foundation for building microscopy applications with pymmcore-plus. Each example focuses on specific functionality while demonstrating best practices for real-world usage.
