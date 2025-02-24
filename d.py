from typing import Literal, NamedTuple

from useq import MDASequence

from pymmcore_plus.metadata.schema import SummaryMetaV1


def position_sizes(seq: MDASequence) -> list[dict[str, int]]:
    """Return a list of size dicts for each position in the sequence.

    There will be one dict for each position in the sequence. Each dict will contain
    `{dim: size}` pairs for each dimension in the sequence. Dimensions with no size
    will be omitted, though singletons will be included.
    """
    main_sizes = dict(seq.sizes)
    main_sizes.pop("p", None)  # remove position

    if not seq.stage_positions:
        # this is a simple MDASequence
        return [{k: v for k, v in main_sizes.items() if v}]

    sizes = []
    for p in seq.stage_positions:
        if p.sequence is not None:
            psizes = {k: v or main_sizes.get(k, 0) for k, v in p.sequence.sizes.items()}
        else:
            psizes = main_sizes.copy()
        sizes.append({k: v for k, v in psizes.items() if v and k != "p"})
    return sizes


def _build_dims(seq: MDASequence, meta: SummaryMetaV1) -> list[Dimension]:
    sizes = position_sizes(seq)

    # OME NGFF is pretty strict about dimensions... there may not be more than 5
    # and they MUST be ordered by type: time, channel, space
    dims: list[Dimension] = []
    # for key in (useq.Axis.TIME, useq.Axis.CHANNEL, useq.Axis.Z):
    for key in sizes:
        if nt := sizes.get(key):
            dims.append(
                Dimension(
                    label=key,
                    size=nt,
                    unit=_get_unit(key, self.current_sequence),
                ),
            )

    img_info = meta["image_infos"][0]
    px_unit = (img_info.get("pixel_size_um", 1), "um")
    ny, nx = img_info["plane_shape"]
    y = Dimension(label="y", size=ny, unit=px_unit)
    x = Dimension(label="x", size=nx, unit=px_unit)
    dims.extend([y, x])
    return dims


OME_DIM_TYPE = {"y": "space", "x": "space", "z": "space", "t": "time", "c": "channel"}
OME_UNIT = {"um": "micrometer", "ml": "milliliter", "s": "second", None: "unknown"}


class Dimension(NamedTuple):
    label: str
    size: int
    unit: tuple[float, str] | None = None
    # None or 0 indicates no constraint.
    # -1 indicates that the chunk size should equal the full extent of the domain.
    chunk_size: int | None = 1

    @property
    def ome_dim_type(self) -> Literal["space", "time", "channel", "other"]:
        return OME_DIM_TYPE.get(self.label, "other")  # type: ignore

    @property
    def ome_unit(self) -> str:
        if isinstance(self.unit, tuple):
            return OME_UNIT.get(self.unit[1], "unknown")
        return "unknown"

    @property
    def ome_scale(self) -> float:
        if isinstance(self.unit, tuple):
            return self.unit[0]
        return 1.0
