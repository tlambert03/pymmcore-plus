from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import tensorstore as ts
import useq

from ez_tensorstore.schema import ChunkSize, IndexDomain, Schema

from ._5d_writer_base import OMEWriterBase

if TYPE_CHECKING:
    from collections.abc import Sequence
    from os import PathLike
    from typing import Literal, TypeAlias

    import numpy as np
    import tensorstore as ts

    from pymmcore_plus.metadata import FrameMetaV1, SummaryMetaV1

    TsDriver: TypeAlias = Literal["zarr", "zarr3", "n5", "neuroglancer_precomputed"]
    EventKey: TypeAlias = frozenset[tuple[str, int]]


class TensorstoreOMEZarrHandler(OMEWriterBase["ts.TensorStore"]):  # type: ignore[type-var]
    def __init__(
        self,
        *,
        driver: TsDriver = "zarr3",
        path: str | PathLike | None = None,
        delete_existing: bool = False,
        chunks: dict[str, int] | None = None,
        ome_version: str = "0.5",
    ) -> None:
        if ome_version != "0.5":
            msg = "Only OME-Zarr version 0.5 is currently supported."
            raise ValueError(msg)

        try:
            import tensorstore
        except ImportError as e:
            msg = "Tensorstore is required to use this handler."
            raise ImportError(msg) from e

        self._ts = tensorstore
        # NOTE!!
        # tensorstore creates zarr ARRAYS, not GROUPS.
        # But in order to support OME-Zarr, we need to create a group.
        # We create a subdir in the path, and store the array there.
        self._array_path = "0"

        self.ts_driver = driver
        self._group_path: Path | None = None
        self.group_path = path  # type: ignore
        self.delete_existing = delete_existing
        self.chunks = chunks or {}

        self._futures: list[ts.Future | ts.WriteFutures] = []
        self._frame_metadatas: list[tuple[useq.MDAEvent, FrameMetaV1]] = []
        self._current_sequence: useq.MDASequence | None = None
        self._store: ts.TensorStore | None = None
        self._dims: list[_Dim] = []

    @property
    def group_path(self) -> Path | None:
        """Return the path to the zarr group, or None if in-memory."""
        return self._group_path

    @group_path.setter
    def group_path(self, path: str | PathLike | None) -> None:
        """Set the path to the zarr group."""
        if path is None or str(path).lower().startswith("memory:"):
            self.kvstore = "memory://"
            self._group_path = None
        else:
            self._group_path = path = Path(path).expanduser().absolute().resolve()
            self.kvstore = f"file://{path / self._array_path}"

    def reset(self, sequence: useq.MDASequence) -> None:
        """Reset state to prepare for new `sequence`."""
        self._store = None
        self._futures.clear()
        self._frame_metadatas.clear()

    def prepare_sequence(self, seq: useq.MDASequence, meta: SummaryMetaV1) -> None:
        # place to raise an exception?
        super().prepare_sequence(seq, meta)
        if len(seq.used_axes) > 3:
            raise ValueError(
                "Only 5D data (or less) is currently supported by OME-NGFF."
            )
        if any(
            x not in (useq.Axis.TIME, useq.Axis.CHANNEL, useq.Axis.Z)
            for x in seq.used_axes
        ):
            raise ValueError(
                "Only time, channel, and z are currently supported by OME-NGFF."
            )
        for size in positi
        self._create_store(seq, meta)

    def new_array(
        self, position_key: str, dtype: np.dtype, dim_sizes: dict[str, int]
    ) -> ts.TensorStore:
        spec = self._create_spec(seq, meta)
        self._create_group()
        self._store = self._ts.open(spec).result()
        return self._store

    def frameReady(
        self,
        frame: np.ndarray,
        event: useq.MDAEvent,
        meta: FrameMetaV1,
        /,
    ) -> None:
        """Write frame to the tensorstore."""
        keys, values = zip(*event.index.items())
        ts_index = self._ts.d[keys][values]

        # write the new frame asynchronously
        future = self._store[ts_index].write(frame)  # type: ignore
        self._futures.append(future)
        # store, but do not process yet, the frame metadata
        self._frame_metadatas.append((event, meta))

    def _create_group(self) -> None:
        if self.group_path is not None:
            self.group_path.mkdir(parents=True, exist_ok=True)
            group_zarr = self.group_path / "zarr.json"
            group_zarr.write_text(json.dumps(self._group_meta(), indent=2))

    def _group_meta(self) -> dict:
        axes, scales = _ome_axes_scales(self._dims)
        scale0 = {
            "axes": axes,
            "datasets": [
                {
                    "path": self._array_path,
                    "coordinateTransformations": [{"scale": scales, "type": "scale"}],
                },
            ],
        }
        attrs = {"ome": {"version": "0.5", "multiscales": [scale0]}}
        return {"zarr_format": 3, "node_type": "group", "attributes": attrs}

    def _build_dims(self, seq: useq.MDASequence, meta: SummaryMetaV1) -> list[_Dim]:
        # OME NGFF is pretty strict about dimensions... there may not be more than 5
        # and they MUST be ordered by type: time, channel, space
        dims: list[_Dim] = []
        # for key in (useq.Axis.TIME, useq.Axis.CHANNEL, useq.Axis.Z):
        for key in seq.sizes:
            if nt := seq.sizes.get(key):
                dims.append(
                    _Dim(
                        label=key,
                        size=nt,
                        unit=_get_unit(key, seq),
                        chunk_size=self.chunks.get(str(key), 1),
                    ),
                )

        img_info = meta["image_infos"][0]
        px_unit = (img_info.get("pixel_size_um", 1), "um")
        ny, nx = img_info["plane_shape"]
        y = _Dim(label="y", size=ny, unit=px_unit, chunk_size=self.chunks.get("y", -1))
        x = _Dim(label="x", size=nx, unit=px_unit, chunk_size=self.chunks.get("x", -1))
        dims.extend([y, x])
        return dims

    def _create_spec(self, seq: useq.MDASequence, meta: SummaryMetaV1) -> dict:
        self._dims = self._build_dims(seq, meta)
        labels, shape, units, chunk_shape = zip(*self._dims)
        labels = tuple(str(x) for x in labels)
        return {
            "driver": self.ts_driver,
            "kvstore": self.kvstore,
            "schema": Schema(
                domain=IndexDomain(shape=shape, labels=labels),
                dtype=meta["image_infos"][0]["dtype"],  # type: ignore
                chunk_layout={"chunk": {"shape": chunk_shape}},
                dimension_units=units,
            ),
            "create": True,
            "delete_existing": self.delete_existing,
        }


def _get_unit(k: str, seq: useq.MDASequence) -> tuple[float, str] | None:
    """Return (mag, unit) tuple for dimension `k`."""
    if k == useq.Axis.Z and seq.z_plan and hasattr(seq.z_plan, "step"):
        return (seq.z_plan.step, "um")
    if k == useq.Axis.TIME and seq.time_plan and hasattr(seq.time_plan, "interval"):
        if intvl := seq.time_plan.interval.seconds:
            return (intvl, "s")
        return (1e-6, "s")
    return None


def _ome_axes_scales(dims: Sequence[_Dim]) -> tuple[list[dict], list[float]]:
    """Return ome axes meta.

    The length of "axes" must be between 2 and 5 and MUST be equal to the
    dimensionality of the zarr arrays storing the image data. The "axes" MUST
    contain 2 or 3 entries of "type:space" and MAY contain one additional
    entry of "type:time" and MAY contain one additional entry of
    "type:channel" or a null / custom type. The order of the entries MUST
    correspond to the order of dimensions of the zarr arrays. In addition, the
    entries MUST be ordered by "type" where the "time" axis must come first
    (if present), followed by the "channel" or custom axis (if present) and
    the axes of type "space".
    """
    # NOTE: dims should already be sorted properly by _build_dims
    axes: list[dict] = []
    scales: list[float] = []
    for dim in dims:
        axes.append(
            {
                "name": dim.label,
                "type": dim.ome_dim_type,
                "unit": dim.ome_unit,
            },
        )
        scales.append(dim.ome_scale)
    return axes, scales


OME_DIM_TYPE = {"y": "space", "x": "space", "z": "space", "t": "time", "c": "channel"}
OME_UNIT = {"um": "micrometer", "ml": "milliliter", "s": "second", None: "unknown"}


class _Dim(NamedTuple):
    label: str
    size: int
    unit: tuple[float, str] | None = None
    chunk_size: ChunkSize | None = 1  # use -1 for chunk size equal to the full domain

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
