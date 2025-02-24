from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple

import useq

if TYPE_CHECKING:
    from collections.abc import Iterable

ny, nx = 512, 512
OneChannel = ["Cy5"]
TwoChannels = [*OneChannel, "FITC"]
TimePlan2 = useq.TIntervalLoops(interval=0.1, loops=2)
TimePlan3 = useq.TIntervalLoops(interval=0.1, loops=2)
TwoPositions = [(222, 1, 1), (111, 0, 0)]
Grid2x2 = useq.GridRowsColumns(rows=2, columns=2, mode="row_wise_snake")
ZPlan = useq.ZRangeAround(range=0.3, step=0.1)
WellPlan = useq.WellPlatePlan(
    plate=96,
    a1_center_xy=(0, 0),
    rotation=0,
    selected_wells=([1, 2, 3, 4], [5, 6, 7, 8]),  # 4 wells
    well_points_plan=useq.RandomPoints(num_points=3),
)

SIMPLE_MDA = useq.MDASequence(channels=TwoChannels, time_plan=TimePlan2)
MULTIPOINT_MDA = SIMPLE_MDA.replace(stage_positions=TwoPositions)
WELLPLATE_MDA = SIMPLE_MDA.replace(stage_positions=WellPlan)
GRID_MDA = SIMPLE_MDA.replace(grid_plan=Grid2x2)
FULL_MDA = MULTIPOINT_MDA.replace(z_plan=ZPlan)
SUBSEQ_MDA = FULL_MDA.replace(
    channels=OneChannel,
    time_plan=TimePlan3,
    stage_positions=[
        (222, 1, 1),
        useq.Position(
            x=0,
            y=0,
            sequence=useq.MDASequence(
                grid_plan=useq.GridRowsColumns(rows=2, columns=1),
                z_plan=useq.ZRangeAround(range=3, step=1),
            ),
        ),
    ],
)

CUSTOM_SEQ = list(SIMPLE_MDA)
# insert a custom event every 5 events
for i in range(5, len(CUSTOM_SEQ), 5):
    CUSTOM_SEQ.insert(i, useq.MDAEvent(action=useq.CustomAction()))


print(list(WELLPLATE_MDA))

CASES: dict[str, Iterable[useq.MDAEvent]] = {
    "SIMPLE_MDA": SIMPLE_MDA,
    "MULTIPOINT_MDA": MULTIPOINT_MDA,
    "WELLPLATE_MDA": WELLPLATE_MDA,
    "GRID_MDA": GRID_MDA,
    "FULL_MDA": FULL_MDA,
    "SUBSEQ_MDA": SUBSEQ_MDA,
    "CUSTOM_SEQ": CUSTOM_SEQ,
}


class Dimension(NamedTuple):
    """Metadata for a dimension of a dataset."""

    name: str
    size: int
    unit: str | None = None
    kind: Literal["space", "time", "channel", "other"] | None = None
    chunks_size: int = 1
    chunks_per_shard: int = 1


def jagged_sizes(
    seq: useq.MDASequence, compressed: bool = False
) -> dict[str, int | list[dict[str, int]]]:
    """Sizes of the sequence, including jagged sizes for nested sequences.

    If any of the axes (such as stage_positions) have nested sequences, the sizes
    for that dimension will be a list of sizes ({axis: size}) for each index of
    in that axis.

    Examples
    --------
    >>> seq = useq.MDASequence(
            channels=["DAPI", "FITC"],
            stage_positions=[
                (1, 2, 3),
                {
                    "x": 4,
                    "y": 5,
                    "z": 6,
                    "sequence": useq.MDASequence(
                        channels=["Cy5"], grid_plan={"rows": 2, "columns": 1}
                    ),
                },
            ],
            time_plan={"interval": 0, "loops": 3},
            z_plan={"range": 2, "step": 0.7},
        )
    >>> jagged_sizes(seq)
    {'p': [{'t': 3, 'c': 2, 'z': 4}, {'t': 3, 'g': 2, 'c': 1, 'z': 4}]}
    # compressed=True will remove common values from the nested sizes
    >>> jagged_sizes(seq, compressed=True)
    {'t': 3, 'z': 4, 'p': [{'c': 2}, {'g': 2, 'c': 1}]}
    """
    sizes: dict = {k: v for k, v in seq.sizes.items() if v}
    if any(p.sequence is not None for p in seq.stage_positions):
        sub_sizes: list[dict[str, int]] = []
        for p in seq.stage_positions:
            # if p.sequence is None, inherit sizes from the parent sequence
            # if a size doesn't exist, omit it from the sub-sizes
            items = sizes.items() if p.sequence is None else p.sequence.sizes.items()
            sub_sizes.append(
                {
                    k: val
                    for k, v in items
                    if k != useq.Axis.POSITION and (val := v or sizes.get(k))
                }
            )
        sizes = {useq.Axis.POSITION: sub_sizes}
    return sizes


# def make_dims(events: Iterable[useq.MDAEvent]) -> list[Dimension]:
#     """Create a list of dimensions from a sequence of MDA events."""
#     dims = [
#         Dimension(name="channel", size=len(events[0].channels), kind="channel"),
#         Dimension(name="time", size=len(events), unit="s", kind="time"),
#     ]
#     for event in events:
#         if event.stage_positions:
#             dims.append(
#                 Dimension(
#                     name="position",
#                     size=len(event.stage_positions),
#                     kind="space",
#                     chunks_size=1,
#                     chunks_per_shard=1,
#                 )
#             )
#     return dims
from rich import print

for name, case in CASES.items():
    if isinstance(case, useq.MDASequence):
        print(name)
        print(jagged_sizes(case))
    # print(make_dims(case))
    print()
