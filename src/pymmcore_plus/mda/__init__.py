"""Running multi-dimensional acquisitions: the runner, the default engine, and signals.

[`MDARunner`][pymmcore_plus.mda.MDARunner] (available as `core.mda`) runs an
acquisition, and [`MDAEngine`][pymmcore_plus.mda.MDAEngine] (`core.mda.engine`)
drives the hardware for each event.  See [The Acquisition
Engine][the-acquisition-engine] for a guide.
"""

from ._engine import MDAEngine
from ._protocol import PMDAEngine
from ._runner import (
    FinishReason,
    MDARunner,
    RunnerStatus,
    RunState,
    SkipEvent,
    SupportsFrameReady,
)
from ._thread_relay import mda_listeners_connected
from .events import PMDASignaler

__all__ = [
    "FinishReason",
    "MDAEngine",
    "MDARunner",
    "PMDAEngine",
    "PMDASignaler",
    "RunState",
    "RunnerStatus",
    "SkipEvent",
    "SupportsFrameReady",
    "mda_listeners_connected",
]
