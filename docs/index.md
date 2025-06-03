# pymmcore-plus

**pymmcore-plus** is a Python package that extends [pymmcore](https://github.com/micro-manager/pymmcore) (Python bindings for Micro-Manager's C++ core) with additional functionality for microscopy control and automation.

## Key Features

- **Enhanced CMMCore API**: The `CMMCorePlus` class extends the base `CMMCore` with additional methods and capabilities
- **Event System**: Comprehensive callback system for hardware events, property changes, and acquisition monitoring
- **Multi-Dimensional Acquisition (MDA) Engine**: Pure Python acquisition engine for complex imaging experiments
- **Device Management**: Enhanced device abstraction and configuration handling
- **Modern Python Integration**: Type hints, context managers, and Pythonic APIs
- **Extensible Architecture**: Plugin system for custom acquisition strategies and hardware control

## Quick Start

```python
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine, MDASequence
import useq

# Initialize the core
mmc = CMMCorePlus()
mmc.loadSystemConfiguration()  # Load your config file

# Run a simple MDA
sequence = MDASequence(
    channels=[{"config": "DAPI"}, {"config": "FITC"}],
    time_plan={"interval": 1, "loops": 10},
    z_plan={"range": 10, "step": 0.5},
)

engine = MDAEngine(mmc)
engine.run(sequence)
```

## What's Different from pymmcore?

While pymmcore provides direct access to Micro-Manager's core functionality, pymmcore-plus adds:

- **Event-driven programming** with callbacks and signals
- **Higher-level acquisition abstractions** for complex experiments
- **Better error handling** and logging
- **Modern Python features** like context managers and type hints
- **Pure Python MDA engine** that doesn't require the Micro-Manager application

## Architecture Overview

```
pymmcore-plus/
├── core/               # Core functionality and CMMCorePlus class
│   ├── events/         # Event system and callbacks
│   └── _device.py      # Device abstraction classes
├── mda/                # Multi-dimensional acquisition engine
├── install/            # Installation and device management utilities
└── widgets/            # GUI widgets (Qt-based)
```

## Getting Started

1. [Installation](install.md) - Setup and dependencies
2. [Basic Usage](basic-usage.md) - Your first script with pymmcore-plus
3. [Event System](events.md) - Working with callbacks and signals
4. [MDA Engine](mda.md) - Multi-dimensional acquisitions
5. [Device Management](devices.md) - Hardware control and configuration
6. [Examples](examples.md) - Complete examples and use cases