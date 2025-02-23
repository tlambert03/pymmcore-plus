from __future__ import annotations

import useq
from rich import print

from pymmcore_plus.core._mmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers._tensorstore_ome_zarr import TensorstoreOMEZarrHandler

seq = useq.MDASequence(
    time_plan=useq.TIntervalLoops(interval=0, loops=3),
    z_plan=useq.ZRangeAround(range=3, step=0.5),
    channels=["DAPI", "FITC"],
    # axis_order="tzc",
    # stage_positions=[(0, 0), (0, 1), (1, 0)],
)

print(seq.sizes)
# sys.exit()
core = CMMCorePlus()
core.loadSystemConfiguration()

core.mda.run(
    seq,
    output=TensorstoreOMEZarrHandler(
        path="~/Desktop/test.zarr", delete_existing=True, chunks={"y": 128, "x": 128}
    ),
)
