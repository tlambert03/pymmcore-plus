# Multi-Dimensional Acquisition (MDA)

Multi-dimensional acquisition (MDA) is a core feature of pymmcore-plus that enables automated collection of microscopy data across multiple dimensions such as time, Z-stacks, channels, and stage positions. This system provides a powerful and flexible framework for designing complex experimental sequences.

## Overview

The MDA system in pymmcore-plus is built around two key components:
- **MDASequence**: Defines what data to collect and how
- **MDAEngine**: Executes the sequence and manages hardware

The system uses the [useq-schema](https://pymmcore-plus.github.io/useq-schema/) library to define experimental sequences, providing standardized, serializable experiment descriptions.

## Quick Start

Here's a simple example of running an MDA sequence:

```python
import numpy as np
from useq import MDASequence, MDAEvent
from pymmcore_plus import CMMCorePlus

# Create and configure the core
core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# Define a simple sequence
sequence = MDASequence(
    channels=["DAPI", {"config": "FITC", "exposure": 50}],
    time_plan={"interval": 2, "loops": 5},
    z_plan={"range": 4, "step": 0.5},
    axis_order="tpcz",
)

# Connect a callback to handle incoming data
@core.mda.events.frameReady.connect
def on_frame(image: np.ndarray, event: MDAEvent):
    print(f"Received {image.shape} image at position {event.index}")

# Run the sequence
core.run_mda(sequence)
```

## MDASequence Components

An `MDASequence` consists of several plan components that define the experimental dimensions:

### Channel Plans

Channels define different imaging conditions (filters, illumination, exposure times):

```python
from useq import MDASequence, Channel

# Simple channel names (uses default exposure)
sequence = MDASequence(channels=["DAPI", "FITC", "Cy5"])

# Channels with custom exposures
sequence = MDASequence(
    channels=[
        {"config": "DAPI", "exposure": 100},
        {"config": "FITC", "exposure": 50}, 
        Channel(config="Cy5", exposure=200, z_offset=0.5)
    ]
)

# Channels with advanced features
sequence = MDASequence(
    channels=[
        "FITC",  # Take Z-stack in FITC
        {"config": "DAPI", "do_stack": False},  # Single plane in DAPI
        {"config": "BF", "acquire_every": 3}   # BF every 3rd timepoint
    ],
    z_plan={"range": 10, "step": 1},
    time_plan={"loops": 10, "interval": 30}
)
```

### Time Plans

Time plans control temporal sampling:

```python
# Simple time series
time_plan = {"interval": 2.5, "loops": 100}  # Every 2.5 seconds, 100 times

# Duration-based
time_plan = {"interval": 1, "duration": 300}  # Every 1 second for 5 minutes

# Complex timing with phases
time_plan = [
    {"interval": 0.1, "loops": 10},  # Fast sampling for 10 frames
    {"interval": 5.0, "loops": 50}   # Then slower sampling
]
```

### Z Plans

Z plans define Z-stack acquisition:

```python
# Range around current position
z_plan = {"range": 10, "step": 0.5}  # ±5 μm around current Z

# Absolute positions
z_plan = {"top": 100, "bottom": 80, "step": 0.2}

# Relative positions
z_plan = {"above": 5, "below": 5, "step": 1}

# Explicit positions
z_plan = [95, 96, 97, 98, 99, 100, 101]
```

### Stage Positions

Define XY positions for multi-site imaging:

```python
# Simple coordinates
stage_positions = [(100, 200), (150, 250), (200, 300)]

# Named positions with metadata
stage_positions = [
    {"x": 100, "y": 200, "name": "Cell 1"},
    {"x": 150, "y": 250, "name": "Cell 2", "z": 50}
]

# Position objects with sub-sequences
from useq import Position
stage_positions = [
    Position(x=100, y=200, name="Site 1"),
    Position(
        x=200, y=300, 
        name="Site 2",
        sequence=MDASequence(  # Sub-sequence at this position
            grid_plan={"rows": 3, "columns": 3},
            z_plan={"range": 5, "step": 1}
        )
    )
]
```

### Grid Plans

Automated grid acquisition for large areas:

```python
# Simple grid
grid_plan = {"rows": 5, "columns": 4}

# Grid with overlap and movement patterns
grid_plan = {
    "rows": 10, 
    "columns": 8,
    "overlap": 0.1,  # 10% overlap
    "mode": "row_wise_snake",  # Movement pattern
    "fov_width": 100,   # Field of view in microns
    "fov_height": 100
}
```

## Axis Order

The `axis_order` parameter controls the nesting of acquisition loops:

```python
# Time -> Position -> Channel -> Z (outer to inner loops)
sequence = MDASequence(
    axis_order="tpcz",
    time_plan={"loops": 5, "interval": 60},
    stage_positions=[(0, 0), (100, 100)],
    channels=["DAPI", "FITC"],
    z_plan={"range": 10, "step": 2}
)

# This will:
# 1. For each timepoint (t=0,1,2,3,4):
#    2. For each position (p=0,1):
#       3. For each channel (c=0,1):
#          4. Take complete Z-stack (z=0,1,2,3,4)
```

Common patterns:
- `"tpcz"`: Time-lapse with position changes
- `"ptcz"`: Visit all positions before next timepoint
- `"tcz"`: Simple time-lapse with channels and Z
- `"czp"`: Channel and Z stacks at each position

## Data Handling

### Event Callbacks

Connect to MDA events to process data as it's acquired:

```python
@core.mda.events.frameReady.connect
def save_frame(image: np.ndarray, event: MDAEvent):
    # Process each frame
    filename = f"img_t{event.index.get('t', 0):03d}_p{event.index.get('p', 0):02d}.tif"
    # Save using your preferred method
    pass

@core.mda.events.sequenceStarted.connect  
def on_start(sequence: MDASequence):
    print(f"Starting acquisition: {sequence.uid}")

@core.mda.events.sequenceFinished.connect
def on_finish(sequence: MDASequence):
    print("Acquisition complete!")
```

### Built-in Writers

Pymmcore-plus provides several built-in data writers:

```python
from pymmcore_plus.mda import mda_listeners_connected
from pymmcore_plus.mda.handlers import (
    OMETiffWriter, 
    OMEZarrWriter, 
    ImageSequenceWriter,
    TensorStoreHandler
)

# OME-TIFF format
with mda_listeners_connected(OMETiffWriter("experiment.ome.tiff")):
    core.mda.run(sequence)

# OME-Zarr format for large datasets
writer = OMEZarrWriter("experiment.zarr", overwrite=True)
with mda_listeners_connected(writer):
    core.mda.run(sequence)

# Image sequence (individual files)
writer = ImageSequenceWriter(
    "data_folder", 
    extension=".tiff",
    prefix="img_",
    include_frame_count=True
)
with mda_listeners_connected(writer):
    core.mda.run(sequence)

# TensorStore for cloud storage
writer = TensorStoreHandler("experiment.zarr", driver="zarr")
core.mda.run(sequence, output=writer)
```

## Hardware Sequencing

Pymmcore-plus can use hardware-triggered sequences for improved performance:

```python
# Enable hardware sequencing (default)
core.mda.engine.use_hardware_sequencing = True

# Check if events can be hardware sequenced
from useq import MDAEvent
event1 = MDAEvent(exposure=50, channel="DAPI")
event2 = MDAEvent(exposure=50, channel="FITC")

can_sequence = core.canSequenceEvents(event1, event2)
print(f"Can sequence: {can_sequence}")

# Hardware sequencing automatically groups compatible events
# for faster execution when devices support it
```

## Advanced Features

### Keeping Shutters Open

Minimize photo-damage by keeping shutters open during fast sequences:

```python
sequence = MDASequence(
    z_plan={"range": 10, "step": 0.5},
    channels=["FITC", "DAPI"],
    keep_shutter_open_across="z"  # Keep open during Z-stack
)
```

### Autofocus

Integrate autofocus into acquisition sequences:

```python
sequence = MDASequence(
    stage_positions=[(0, 0), (100, 100), (200, 200)],
    time_plan={"loops": 10, "interval": 300},
    autofocus_plan={
        "autofocus_motor_offset": 25,
        "axes": ("p", "t")  # Autofocus at each position and timepoint
    }
)
```

### Conditional Acquisition

Use custom iterables for smart/adaptive imaging:

```python
def adaptive_sequence(core):
    """Example of adaptive imaging based on previous results"""
    for t in range(100):
        # Take initial image
        event = MDAEvent(index={"t": t}, channel="DAPI")
        yield event
        
        # Analyze previous frame (simplified)
        if some_analysis_condition():
            # Take additional channels if needed
            yield MDAEvent(index={"t": t, "c": 1}, channel="FITC")
            yield MDAEvent(index={"t": t, "c": 2}, channel="Cy5")

# Run adaptive sequence
core.run_mda(adaptive_sequence(core))
```

## Sequence Serialization

MDA sequences can be saved and loaded as YAML or JSON:

```python
# Create sequence
sequence = MDASequence(
    channels=["DAPI", "FITC"],
    time_plan={"interval": 30, "loops": 100},
    z_plan={"range": 10, "step": 1}
)

# Save to file
with open("experiment.yaml", "w") as f:
    f.write(sequence.yaml())

# Load from file
loaded_sequence = MDASequence.from_file("experiment.yaml")

# Run from command line
# mmcore run experiment.yaml --config my_config.cfg
```

## Control and Monitoring

### Pausing and Canceling

```python
# Start sequence in background
thread = core.run_mda(sequence)

# Control execution
core.mda.toggle_pause()  # Pause/resume
core.mda.cancel()       # Cancel sequence

# Wait for completion
thread.join()
```

### Progress Monitoring

```python
@core.mda.events.sequenceStarted.connect
def track_progress(sequence: MDASequence):
    total_events = len(list(sequence))
    print(f"Total events: {total_events}")

@core.mda.events.frameReady.connect
def update_progress(image, event: MDAEvent):
    # Calculate progress based on event indices
    progress = calculate_progress(event.index)
    print(f"Progress: {progress:.1%}")
```

## Best Practices

### Memory Management
- Use appropriate data writers for large datasets
- Consider Zarr format for multi-GB acquisitions
- Process data in chunks when possible

### Performance Optimization
- Enable hardware sequencing when available
- Use appropriate exposure times and intervals
- Consider pre-loading device configurations

### Error Handling
```python
@core.mda.events.sequencePauseToggled.connect
def on_pause(paused: bool):
    print(f"Sequence {'paused' if paused else 'resumed'}")

@core.mda.events.sequenceCanceled.connect  
def on_cancel(sequence: MDASequence):
    print("Sequence was canceled")
    # Cleanup code here

try:
    core.run_mda(sequence)
except Exception as e:
    print(f"Acquisition failed: {e}")
    # Handle error
```

### Experimental Design
- Test sequences with short durations first
- Validate timing requirements before long experiments
- Use position lists for reproducible multi-site imaging
- Consider stage drift and focus stability for long acquisitions

## Integration Examples

### With Napari
```python
import napari
from pymmcore_plus.mda.handlers import NapariHandler

viewer = napari.Viewer()
handler = NapariHandler(viewer)

with mda_listeners_connected(handler):
    core.mda.run(sequence)
```

### With Analysis Pipelines
```python
@core.mda.events.frameReady.connect
def analyze_frame(image: np.ndarray, event: MDAEvent):
    # Real-time analysis
    if event.channel.config == "DAPI":
        nuclei_count = count_nuclei(image)
        print(f"Found {nuclei_count} nuclei at {event.index}")
```

## Troubleshooting

### Common Issues
- **Timing drift**: Use hardware sequencing when available
- **Focus loss**: Enable autofocus or use z-drift correction
- **Memory issues**: Use streaming writers for large datasets
- **Device conflicts**: Check device compatibility with sequencing

### Debugging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check sequence validity
events = list(sequence)
print(f"Sequence has {len(events)} events")

# Test individual events
test_event = events[0]
core.mda.engine.execute_event(test_event)
```

The MDA system provides a comprehensive foundation for automated microscopy experiments, from simple time-lapse imaging to complex multi-dimensional studies. Its flexibility allows adaptation to diverse experimental needs while maintaining performance and reliability.