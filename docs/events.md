# Event System

pymmcore-plus provides a comprehensive event system that allows you to write reactive, event-driven microscopy applications. The event system is built around Qt signals and provides callbacks for hardware changes, property updates, and acquisition events.

## Overview

The event system in pymmcore-plus allows you to:

- React to hardware state changes
- Monitor property updates in real-time
- Track acquisition progress
- Handle errors and system events
- Build responsive user interfaces

## Core Event Classes

### CMMCoreSignaler

The main event hub is accessible via `mmc.events`:

```python
from pymmcore_plus import CMMCorePlus

mmc = CMMCorePlus()
events = mmc.events  # CMMCoreSignaler instance
```

### Key Event Categories

1. **System Events**: Configuration changes, device initialization
2. **Property Events**: Property value changes
3. **Acquisition Events**: Image acquisition, sequence progress
4. **Stage Events**: Position changes, movement completion
5. **Error Events**: Hardware errors, exceptions

## Basic Event Usage

### Connecting to Events

```python
from pymmcore_plus import CMMCorePlus

def on_property_changed(device: str, property: str, value: str):
    print(f"{device}.{property} changed to: {value}")

def on_image_snapped():
    print("Image captured!")

mmc = CMMCorePlus()

# Connect to events
mmc.events.propertyChanged.connect(on_property_changed)
mmc.events.imageSnapped.connect(on_image_snapped)

# Load configuration and snap image
mmc.loadSystemConfiguration()
mmc.snapImage()  # Will trigger the imageSnapped event
```

### Using Lambda Functions

```python
# Quick event handlers with lambda
mmc.events.systemConfigurationLoaded.connect(
    lambda: print("System ready!")
)

mmc.events.xYPositionChanged.connect(
    lambda x, y: print(f"Stage moved to ({x:.2f}, {y:.2f})")
)
```

## Property Monitoring

### Automatic Property Watching

```python
from pymmcore_plus import CMMCorePlus

def monitor_camera_properties(device: str, property: str, value: str):
    if device == "Camera":
        print(f"Camera {property}: {value}")

mmc = CMMCorePlus()
mmc.events.propertyChanged.connect(monitor_camera_properties)

# Enable automatic property monitoring
mmc.loadSystemConfiguration()

# Changes will now trigger events
mmc.setProperty("Camera", "Binning", "2x2")
mmc.setProperty("Camera", "Exposure", "100")
```

### Manual Property Watching

```python
# Watch specific properties
def on_exposure_changed(device: str, property: str, value: str):
    if property == "Exposure":
        print(f"Exposure changed to {value}ms")

mmc.events.propertyChanged.connect(on_exposure_changed)

# Or use device-specific events if available
camera = mmc.getDevice("Camera")
if hasattr(camera, 'exposureChanged'):
    camera.exposureChanged.connect(lambda exp: print(f"New exposure: {exp}"))
```

## Acquisition Events

### Image Acquisition Monitoring

```python
def on_image_snapped():
    image = mmc.getImage()
    print(f"Image acquired: {image.shape}")

def on_sequence_started(length: int):
    print(f"Sequence started: {length} images")

def on_sequence_finished():
    print("Sequence completed")

mmc.events.imageSnapped.connect(on_image_snapped)
mmc.events.sequenceStarted.connect(on_sequence_started)
mmc.events.sequenceFinished.connect(on_sequence_finished)

# Start a sequence
mmc.startSequenceAcquisition(10, 100, True)  # 10 images, 100ms interval
```

### MDA Events

For Multi-Dimensional Acquisitions, additional events are available:

```python
from pymmcore_plus.mda import MDAEngine

def on_mda_started(sequence):
    print(f"MDA started: {len(sequence)} events")

def on_mda_frame_ready(image, event):
    print(f"Frame ready: t={event.index.get('t', 0)}, z={event.index.get('z', 0)}")

def on_mda_finished():
    print("MDA completed!")

engine = MDAEngine(mmc)
engine.events.sequenceStarted.connect(on_mda_started)
engine.events.frameReady.connect(on_mda_frame_ready)
engine.events.sequenceFinished.connect(on_mda_finished)
```

## Stage and Position Events

### XY Stage Monitoring

```python
def on_xy_position_changed(x: float, y: float):
    print(f"XY stage moved to: ({x:.2f}, {y:.2f})")

def on_stage_position_changed(device: str, position: float):
    print(f"Stage {device} moved to: {position:.2f}")

mmc.events.xYPositionChanged.connect(on_xy_position_changed)
mmc.events.stagePositionChanged.connect(on_stage_position_changed)

# Move stage (will trigger events)
mmc.setXYPosition(100, 200)
mmc.setPosition(50)  # Z stage
```

## Error Handling with Events

### System Error Events

```python
def on_system_error(device: str, code: int, message: str):
    print(f"System error from {device}: {message} (code: {code})")

def on_device_error(device: str, code: int, message: str):
    print(f"Device error from {device}: {message}")

mmc.events.systemError.connect(on_system_error)
mmc.events.deviceError.connect(on_device_error)
```

## Advanced Event Patterns

### Event Filtering

```python
class CameraEventFilter:
    def __init__(self, mmc):
        self.mmc = mmc
        mmc.events.propertyChanged.connect(self.on_property_changed)
    
    def on_property_changed(self, device: str, property: str, value: str):
        if device == "Camera" and property in ["Exposure", "Binning", "Gain"]:
            print(f"Important camera property changed: {property} = {value}")

filter = CameraEventFilter(mmc)
```

### Event Buffering

```python
from collections import deque
from datetime import datetime

class EventLogger:
    def __init__(self, mmc, max_events=1000):
        self.events = deque(maxlen=max_events)
        mmc.events.propertyChanged.connect(self.log_property_change)
        mmc.events.imageSnapped.connect(self.log_image_snap)
    
    def log_property_change(self, device: str, property: str, value: str):
        self.events.append({
            'timestamp': datetime.now(),
            'type': 'property_changed',
            'device': device,
            'property': property,
            'value': value
        })
    
    def log_image_snap(self):
        self.events.append({
            'timestamp': datetime.now(),
            'type': 'image_snapped'
        })
    
    def get_recent_events(self, n=10):
        return list(self.events)[-n:]

logger = EventLogger(mmc)
```

### Conditional Event Handling

```python
class SmartAcquisition:
    def __init__(self, mmc):
        self.mmc = mmc
        self.auto_focus_enabled = True
        mmc.events.xYPositionChanged.connect(self.on_stage_moved)
    
    def on_stage_moved(self, x: float, y: float):
        if self.auto_focus_enabled:
            # Trigger autofocus after stage movement
            self.run_autofocus()
    
    def run_autofocus(self):
        print("Running autofocus...")
        # Implement autofocus logic here

smart_acq = SmartAcquisition(mmc)
```

## Event-Driven Acquisition Example

Here's a complete example of an event-driven acquisition system:

```python
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine, MDASequence
import useq

class EventDrivenAcquisition:
    def __init__(self):
        self.mmc = CMMCorePlus()
        self.engine = MDAEngine(self.mmc)
        self.setup_events()
        
    def setup_events(self):
        # Core events
        self.mmc.events.systemConfigurationLoaded.connect(self.on_config_loaded)
        self.mmc.events.propertyChanged.connect(self.on_property_changed)
        
        # MDA events
        self.engine.events.sequenceStarted.connect(self.on_sequence_started)
        self.engine.events.frameReady.connect(self.on_frame_ready)
        self.engine.events.sequenceFinished.connect(self.on_sequence_finished)
        
    def on_config_loaded(self):
        print("System configuration loaded - ready for acquisition")
        
    def on_property_changed(self, device: str, property: str, value: str):
        if device == "Camera" and property == "Exposure":
            print(f"Camera exposure changed to {value}ms")
            
    def on_sequence_started(self, sequence):
        print(f"Starting MDA with {len(sequence)} time points")
        
    def on_frame_ready(self, image, event):
        t = event.index.get('t', 0)
        z = event.index.get('z', 0)
        c = event.index.get('c', 0)
        print(f"Frame captured: t={t}, z={z}, c={c}, shape={image.shape}")
        
    def on_sequence_finished(self):
        print("MDA sequence completed!")
        
    def run_experiment(self):
        # Load configuration
        self.mmc.loadSystemConfiguration()
        
        # Create and run sequence
        sequence = MDASequence(
            time_plan=useq.TIntervalLoops(interval=2, loops=5),
            z_plan=useq.ZRangeAround(range=10, step=1),
            channels=["DAPI", "FITC"]
        )
        
        self.engine.run(sequence)

# Usage
experiment = EventDrivenAcquisition()
experiment.run_experiment()
```

## Integration with GUI Applications

The event system integrates seamlessly with Qt-based applications:

```python
from qtpy.QtWidgets import QApplication, QMainWindow, QLabel
from pymmcore_plus import CMMCorePlus

class MicroscopyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mmc = CMMCorePlus()
        self.status_label = QLabel("Not connected")
        self.setCentralWidget(self.status_label)
        
        # Connect events
        self.mmc.events.systemConfigurationLoaded.connect(
            lambda: self.status_label.setText("System ready")
        )
        
        self.mmc.events.imageSnapped.connect(
            lambda: self.status_label.setText("Image captured")
        )

app = QApplication([])
window = MicroscopyMainWindow()
window.show()
```

## Best Practices

1. **Always disconnect events** when objects are destroyed to prevent memory leaks
2. **Keep event handlers fast** - do heavy processing in separate threads
3. **Use meaningful event handler names** for debugging
4. **Consider event ordering** - some events may be triggered simultaneously
5. **Handle exceptions** in event handlers to prevent crashes

## Next Steps

- Learn about [MDA acquisitions](mda.md) and their event system
- Explore [Basic Usage](basic-usage.md) for more device control examples
