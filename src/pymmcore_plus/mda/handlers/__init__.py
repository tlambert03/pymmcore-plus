"""Deprecated data handlers (writers) for MDA acquisitions.

!!! warning "Deprecated"

    This module is deprecated, and importing it emits a `FutureWarning`.  To save
    data, pass a path ending in `.ome.zarr` or `.ome.tiff` (or an
    [`ome_writers.AcquisitionSettings`][]) as the `output` of
    [`MDARunner.run`][pymmcore_plus.mda.MDARunner.run], which writes with
    [ome-writers](https://pymmcore-plus.github.io/ome-writers/) (see
    [Saving Data][saving-data]).  These handlers will be removed in a future version;
    if you depend on one, please copy it into your own code.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from ._img_sequence_writer import ImageSequenceWriter
from ._ome_tiff_writer import OMETiffWriter
from ._ome_zarr_writer import OMEZarrWriter
from ._tensorstore_handler import TensorStoreHandler

warnings.warn(
    f"The {__name__!r} module is deprecated and will be removed in a "
    "future version. We are moving to ome-writers as the internally supported "
    "data-sink. If you would like to continue using these handlers, please vendor "
    "them into your own codebase.",
    FutureWarning,
    stacklevel=2,
)

__all__ = [
    "ImageSequenceWriter",
    "OMETiffWriter",
    "OMEZarrWriter",
    "TensorStoreHandler",
    "handler_for_path",
]


def handler_for_path(path: str | Path) -> object:
    """Convert a string or Path into a handler object.

    This method picks from the built-in handlers based on the extension of the path.
    """
    if str(path).rstrip("/").rstrip(":").lower() == "memory":
        return TensorStoreHandler(kvstore="memory://")

    path = str(Path(path).expanduser().resolve())
    if path.endswith(".zarr"):
        return OMEZarrWriter(path)

    if path.endswith((".tiff", ".tif")):
        return OMETiffWriter(path)

    # FIXME: ugly hack for the moment to represent a non-existent directory
    # there are many features that ImageSequenceWriter supports, and it's unclear
    # how to infer them all from a single string.
    if not (Path(path).suffix or Path(path).exists()):
        return ImageSequenceWriter(path)

    raise ValueError(f"Could not infer a writer handler for path: '{path}'")
