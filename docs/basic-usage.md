# Basic Usage

This guide covers the fundamentals of using pymmcore-plus for microscopy control.

## CMMCorePlus: The Enhanced Core

The `CMMCorePlus` class is the heart of pymmcore-plus. It extends pymmcore's `CMMCore` with additional functionality while maintaining full compatibility.

```python
from pymmcore_plus import CMMCorePlus

# Create the core instance
mmc = CMMCorePlus()

# Load a system configuration
mmc.loadSystemConfiguration("/path/to/your/config.cfg")

# The core provides the same methods as CMMCore, plus additional features
print(f"Camera: {mmc.getCameraDevice()}")
print(f"Current position: {mmc.getPosition()}")
```

## Key Differences from CMMCore

### 1. Enhanced Error Handling

```python
try:
    mmc.setProperty("Camera", "Binning", "2x2")
except Exception as e:
    print(f"Failed to set binning: {e}")
    # CMMCorePlus provides better error context
```

### 2. Context Manager Support

```python
# Automatically manage core lifecycle
with CMMCorePlus() as mmc:
    mmc.loadSystemConfiguration()
    # Core is automatically cleaned up
```

### 3. Property Access

```python
# Direct property access
binning = mmc.getProperty("Camera", "Binning")
mmc.setProperty("Camera", "Binning", "4x4")

# Or use the device abstraction
camera = mmc.getDevice("Camera")
camera.binning = "2x2"
print(f"Binning: {camera.binning}")
```

## Basic Image Acquisition

### Single Image

```python
from pymmcore_plus import CMMCorePlus
import numpy as np

mmc = CMMCorePlus()
mmc.loadSystemConfiguration()

# Snap a single image
mmc.snapImage()
image = mmc.getImage()

# Image is returned as a numpy array
print(f"Image shape: {image.shape}")
print(f"Image dtype: {image.dtype}")
```

### Live Imaging

```python
# Start continuous acquisition
mmc.startContinuousSequenceAcquisition(0)  # 0ms interval

try:
    while mmc.getRemainingImageCount() > 0 or mmc.isSequenceRunning():
        if mmc.getRemainingImageCount() > 0:
            image = mmc.popNextImage()
            # Process image here
            print(f"Got image: {image.shape}")
finally:
    mmc.stopSequenceAcquisition()
```

## Working with Devices

### Device Discovery

```python
# List all loaded devices
devices = mmc.getLoadedDevices()
print("Loaded devices:", devices)

# Get devices by type
cameras = mmc.getLoadedDevicesOfType(mmc.CameraDevice)
stages = mmc.getLoadedDevicesOfType(mmc.StageDevice)
```

### Stage Control

```python
# XY stage control
xy_stage = mmc.getXYStageDevice()
if xy_stage:
    # Get current position
    x, y = mmc.getXYPosition()
    print(f"Current XY position: ({x}, {y})")
    
    # Move to new position
    mmc.setXYPosition(x + 100, y + 100)
    mmc.waitForDevice(xy_stage)

# Z stage control
z_stage = mmc.getFocusDevice()
if z_stage:
    z = mmc.getPosition()
    print(f"Current Z position: {z}")
    
    mmc.setPosition(z + 5)
    mmc.waitForDevice(z_stage)
```

### Filter Wheels and Objectives

```python
# Work with configuration groups
configs = mmc.getAvailableConfigs("Channel")
print("Available channels:", configs)

# Set a configuration
mmc.setConfig("Channel", "DAPI")
mmc.waitForConfig("Channel", "DAPI")

# Objective control
objective = mmc.getStateDevice("Objective")
if objective:
    position = mmc.getStatePosition(objective)
    label = mmc.getStateLabel(objective)
    print(f"Objective: {label} (position {position})")
```

## Configuration Management

### Loading Configurations

```python
# Load from file
mmc.loadSystemConfiguration("/path/to/config.cfg")

# Load specific device
mmc.loadDevice("Camera", "DemoCamera", "DCam")

# Initialize all devices
mmc.initializeAllDevices()
```

### Saving and Loading System State

```python
# Save current system state
state = mmc.getSystemState()

# Modify some settings
mmc.setProperty("Camera", "Binning", "4x4")

# Restore previous state
mmc.setSystemState(state)
```

## Error Handling Best Practices

```python
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.core.events import CMMCoreSignaler

def handle_error(device: str, code: int, message: str):
    print(f"Error from {device}: {message} (code: {code})")

mmc = CMMCorePlus()

# Connect to error signals
mmc.events.systemConfigurationLoaded.connect(
    lambda: print("Configuration loaded successfully")
)

try:
    mmc.loadSystemConfiguration()
except Exception as e:
    print(f"Failed to load configuration: {e}")
```

## Next Steps

- Learn about the [Event System](events.md) for reactive programming
- Explore [MDA acquisitions](mda.md) for complex imaging experiments
