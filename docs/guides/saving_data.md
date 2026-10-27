# Saving Data

To save the images from an acquisition, pass `output=` to
[`core.mda.run()`][pymmcore_plus.mda.MDARunner.run] (or
[`core.run_mda()`][pymmcore_plus.CMMCorePlus.run_mda]).  Frames are written to
disk as they arrive, by [ome-writers](https://pymmcore-plus.github.io/ome-writers/),
and the extension of the path picks the format:

```python
from pymmcore_plus import CMMCorePlus
import useq

core = CMMCorePlus()
core.loadSystemConfiguration()

sequence = useq.MDASequence(
    stage_positions=[(0, 0, 0), (100, 100, 0)],
    channels=["DAPI", "FITC"],
    time_plan={"interval": 1, "loops": 3},
    z_plan={"range": 4, "step": 1},
)

core.mda.run(sequence, output="experiment.ome.zarr")  # (1)!
```

1. Or `output="experiment.ome.tiff"`.  Note that `mda.run` blocks until the
   acquisition is done, while `run_mda` runs it on another thread (see [The
   Acquisition Engine](mda_engine.md#running-a-very-simple-sequence)).

There are two formats to choose from:

- **`.ome.zarr`** writes an [OME-Zarr](https://ngff.openmicroscopy.org/) (v0.5,
  which is built on Zarr v3).  This works with the default install.
- **`.ome.tiff`** writes OME-TIFF.  This needs [tifffile](https://github.com/cgohlke/tifffile),
  which is what the `io` extra adds:

    ```bash
    pip install "pymmcore-plus[io]"
    ```

    (Without it, you'll get `ValueError: No available backends found for format
    'ome-tiff'`.)  OME-TIFF is a good choice if you want to open the files in
    tools like Fiji (via Bio-Formats).

The shape of the data comes from the sequence.  In the example above, each position
gets a `(t, c, z, y, x)` array of shape `(3, 2, 5, 512, 512)`.  The dimensions are
stored in the order OME expects (time, channel, z, y, x), whatever `axis_order`
you acquired them in.

## Where did the data go?

The path you pass isn't always a single file:

| output | one position | several positions (or a grid plan) |
| --- | --- | --- |
| `experiment.ome.zarr` | a zarr folder holding one image | a zarr folder with one image per position, named after the position if it has a `name` (`A1/`, ...), or numbered (`0/`, `1/`, ...).  With a grid plan, each tile is its own image (`0_0_0/`, `0_1_0/`, ...: position, row, column) |
| `experiment.ome.tiff` | a single file | a folder, `experiment/`, with one file per position (or grid tile): `experiment_p000.ome.tiff`, `experiment_p001.ome.tiff`, ... |

## Running it again (`overwrite`)

If the output already exists, the run fails right away:

```
FileExistsError: Zarr group already exists at .../experiment.ome.zarr. Use overwrite=True to replace it.
```

Pass `overwrite=True` to replace it:

```python
core.mda.run(sequence, output="experiment.ome.zarr", overwrite=True)
```

`run_mda` doesn't take an `overwrite` argument (yet).  To overwrite from
`run_mda`, put it in an [`AcquisitionSettings`](#more-control-with-acquisitionsettings)
object instead: `output=AcquisitionSettings(root_path="experiment.ome.zarr",
overwrite=True)`.

## Opening the data in Python

An OME-TIFF reads straight into a numpy array with tifffile:

```python
import tifffile

data = tifffile.imread("experiment/experiment_p000.ome.tiff")
print(data.shape)  # (3, 2, 5, 512, 512), i.e. (t, c, z, y, x)
```

An OME-Zarr can be read with any reader that supports Zarr v3, for example
[zarr-python](https://zarr.readthedocs.io/) (`pip install zarr`):

```python
import zarr

root = zarr.open_group("experiment.ome.zarr", mode="r")
data = root["0/0"][:]  # (1)!
print(data.shape)  # (3, 2, 5, 512, 512), i.e. (t, c, z, y, x)
```

1. With several positions, `root["0"]` is the image for the first position (or
   `root["A1"]`, if you named it), and `"0"` inside it is the full-resolution
   array.  With a single position there's
   no position level, so the array is just `root["0"]`.  (`list(root)` shows what's
   there.)

Some metadata is saved along with the pixels:

- The summary metadata (devices, properties, pixel size, the `MDASequence`
  itself, etc...; see [`SummaryMetaV1`][pymmcore_plus.metadata.SummaryMetaV1]) is
  stored under a `"pymmcore_plus"` key, in the attributes of the root zarr group
  (`root.attrs["pymmcore_plus"]["summary_metadata"]`) or as an OME-XML annotation
  in the TIFF.
- For each frame, the time (`delta_t`), exposure time, and stage position are
  written into the OME metadata.  The rest of the per-frame metadata that
  `frameReady` emits ([`FrameMetaV1`][pymmcore_plus.metadata.FrameMetaV1]) is *not*
  saved.  If you need it, connect to `frameReady` and store it yourself (see
  [below](#processing-frames-yourself)).

## More control with `AcquisitionSettings`

Instead of a path, `output` also accepts an
[`ome_writers.AcquisitionSettings`][] object, which lets you choose things like
compression, the backend, and whether to overwrite:

```python
from ome_writers import AcquisitionSettings

settings = AcquisitionSettings(
    root_path="experiment.ome.zarr",
    compression="blosc-zstd",
    overwrite=True,
)
core.run_mda(sequence, output=settings)
```

The dimensions (and well-plate layout, if any) are always filled in from the
sequence, so you don't need to (and can't) set them here.  To change the
chunking, use the `dimension_overrides` argument of `mda.run` / `run_mda`,
keyed by dimension name:

```python
core.mda.run(
    sequence,
    output="experiment.ome.zarr",
    dimension_overrides={"y": {"chunk_size": 256}, "x": {"chunk_size": 256}},
)
```

See the [ome-writers documentation](https://pymmcore-plus.github.io/ome-writers/usage/)
for the rest of the `AcquisitionSettings` options.

While an acquisition is running, [`core.mda.get_view()`][pymmcore_plus.mda.MDARunner.get_view]
returns an array-like view of the data written so far.  (`output="memory"` keeps
the data in memory instead of writing a file, which is handy for viewers and
tests.)

## Lists and generators are saved as a flat stack

The array shape is taken from the `MDASequence`.  If you pass anything else (a
list of `MDAEvent`s, a generator, a queue iterator as in [Event-Driven
Acquisition](event_driven_acquisition.md), or a `useq.v2.MDASequence`), there's no
shape to go on, so the frames are written in the order they arrive into one
`(t, y, x)` array of unknown length:

```python
core.mda.run(list(sequence), output="flat.ome.zarr")  # shape (60, 512, 512)
```

The same happens (with a warning in the log) for an `MDASequence` whose positions
have their own sub-sequence with anything other than a `grid_plan` (for example,
[a different z-stack at one
position](../../useq-schema/guides/sequences.md#different-plans-at-different-positions)),
since the positions then don't share one shape.

Each frame's `MDAEvent` (and its `index`) is still available in the `frameReady`
signal, if you need to sort the frames out later.

## Processing frames yourself

To do something else with the images (analysis, a different file format, sending
them somewhere, etc...), connect a callback to the
[`frameReady`][pymmcore_plus.mda.PMDASignaler.frameReady] signal.  It receives up
to three arguments: the image (a numpy array), the `MDAEvent`, and the frame
metadata dict:

```python
import numpy as np


@core.mda.events.frameReady.connect
def on_frame(image: np.ndarray, event: useq.MDAEvent, metadata: dict) -> None:
    print(f"received frame {event.index}: {image.shape}, {image.dtype}")
```

!!! warning "Keep it quick"

    With the default (psygnal) event backend, a `frameReady` callback runs in the
    acquisition thread, so the next event waits until your callback returns.  See
    [Threads](events.md#threads) for details.

If the processing is slow, write a *handler* object instead, and pass it in
`output=`.  A handler is any object with a `frameReady` method (it may also have
`sequenceStarted` and `sequenceFinished` methods).  Handlers are called from a
separate thread, so they don't hold up the acquisition (`mda.run` waits for them
to catch up before it returns).  Here we make a maximum-intensity projection of
each z-stack, while also saving the raw data:

```python
class MaxProjector:
    """Keep a maximum-intensity projection of each z-stack."""

    def sequenceStarted(self, sequence: useq.MDASequence, metadata: dict) -> None:
        self.projections: dict[tuple, np.ndarray] = {}

    def frameReady(
        self, image: np.ndarray, event: useq.MDAEvent, metadata: dict
    ) -> None:
        idx = event.index
        key = (idx.get("p", 0), idx.get("t", 0), idx.get("c", 0))
        if key in self.projections:
            np.maximum(self.projections[key], image, out=self.projections[key])
        else:
            self.projections[key] = image.copy()

    def sequenceFinished(self, sequence: useq.MDASequence) -> None:
        print(f"made {len(self.projections)} projections")


projector = MaxProjector()  # (1)!
core.mda.run(sequence, output=["experiment.ome.zarr", projector], overwrite=True)
```

1. Keep a reference to the handler, so that you can use `projector.projections`
   after the run.

`output` may be a list holding any number of handlers, plus *at most one* path (or
`AcquisitionSettings`).

!!! warning "Deprecated: `pymmcore_plus.mda.handlers`"

    Older versions of pymmcore-plus wrote data with the handler classes in
    `pymmcore_plus.mda.handlers` (`OMEZarrWriter`, `OMETiffWriter`,
    `TensorStoreHandler` and `ImageSequenceWriter`).  These are deprecated in favor
    of `output=` with a path, as described above, and importing the module emits a
    `FutureWarning`.  They will be removed in a future version; if you rely on one,
    please copy it into your own code.

## Next steps

- [Events](../reference/events.md) lists every signal emitted during an acquisition.
- [Event-Driven Acquisition](event_driven_acquisition.md) builds the sequence on
  the fly, based on the data.
- The [`pymmcore_plus.metadata`][pymmcore_plus.metadata] reference describes the
  summary and frame metadata.
