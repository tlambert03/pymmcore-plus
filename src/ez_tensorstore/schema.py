from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias, TypedDict

from annotated_types import Ge, Interval

NonNegativeInt = Annotated[int, Ge(0)]
PositiveInt = Annotated[int, Ge(1)]
NonNegativeFloat = Annotated[float, Ge(0)]


# A TensorStore data type.
#
# TensorStore data types correspond to the logical data representation, not the precise
# encoding. There are not separate data types for little endian and big endian byte
# order.
DType: TypeAlias = Literal[
    "bfloat16",
    "bool",
    "complex128",
    "complex64",
    "float16",
    "float32",
    "float64",
    "int4",
    "int8",
    "int16",
    "int32",
    "int64",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "ustring",
    "string",
    "json",
    "float8_e5m2fnuz",
    "float8_e5m2",
    "float8_e4m3fnuz",
    "float8_e4m3fn",
    "float8_e4m3b11fnuz",
    "char",
    "byte",
]


class IndexDomain(TypedDict, total=False):
    """Index domains may be serialized to/from JSON using the following schema.

    If neither inclusive_min nor shape is specified, all dimensions receive an implicit
    lower bound of . If shape is specified but inclusive_min is not specified, all
    dimensions receive an explicit lower bound of 0.

    At most one of exclusive_max, inclusive_max, and shape may be specified. If none are
    specified, all dimensions receive an implicit upper bound of .
    """

    rank: Annotated[int, Interval(0, 32)]
    """Number of dimensions.

    The rank must be specified either directly, or implicitly by the number of
    dimensions specified for inclusive_min, inclusive_max, exclusive_max, shape, or
    labels.
    """

    inclusive_min: list[int | list[int]]
    """Inclusive lower bounds of the domain.

    Length must equal the rank. Bounds specified as n indicate normal, explicit bounds,
    while bounds specified as [n] indicate implicit bounds. For example, [1, [2]]
    specifies an explicit bound of  for the first dimension and an implicit bound of
    for the second dimension.
    """

    exclusive_max: list[int | list[int]]
    """Exclusive upper bounds of the domain.

    Length must equal the rank. As for inclusive_min, bounds specified as n indicate
    normal, explicit bounds, while bounds specified as [n] indicate implicit bounds. For
    example, [5, [7]] specifies an explicit bound of  for the first dimension and an
    implicit bound of  for the second dimension.
    """

    inclusive_max: list[int | list[int]]
    """Inclusive upper bounds of the domain.

    Length must equal the rank. As for inclusive_min, bounds specified as n indicate
    normal, explicit bounds, while bounds specified as [n] indicate implicit bounds. For
    example, [5, [7]] specifies an explicit bound of  for the first dimension and an
    implicit bound of  for the second dimension.
    """

    shape: list[int | list[int]]
    """Extent of each dimension of the domain.

    Length must equal the rank. As for inclusive_min, bounds specified as n indicate
    normal, explicit bounds, while bounds specified as [n] indicate implicit bounds. For
    example, assuming an inclusive_min of [1, 2], an shape of [5, [7]] specifies an
    explicit bound of  for the first dimension and an implicit bound of  for the second
    dimension.
    """

    labels: list[str]
    """Dimension labels for each dimension.

    Length must equal the rank. An empty string indicates an unlabeled dimension.
    Non-empty strings must not occur more than once. By default, all dimensions are
    unlabeled.
    """


class ChunkLayoutGrid(TypedDict, total=False):
    """Constraints on the write/read/codec chunk grids.

    When creating a new TensorStore, the chunk shape can be specified directly using the
    shape and shape_soft_constraint members, or indirectly by specifying the
    aspect_ratio and target number of elements.

    When opening an existing TensorStore, the preferences indicated by
    shape_soft_constraint, aspect_ratio, aspect_ratio_soft_constraint, elements, and
    elements_soft_constraint are ignored; only shape serves as a constraint.
    """

    shape: list[NonNegativeInt] | Literal[-1] | None
    """Hard constraints on the chunk size for each dimension.

    The length must equal the rank of the index space. Each element constrains the chunk
    size for the corresponding dimension, and must be a non-negative integer. The
    special value of 0 (or, equivalently, null)for a given dimension indicates no
    constraint. The special value of -1 for a given dimension indicates that the chunk
    size should equal the full extent of the domain, and is always treated as a soft
    constraint.
    """

    shape_soft_constraint: list[NonNegativeInt] | Literal[-1] | None
    """Preferred chunk sizes for each dimension.

    If a non-zero, non-null size for a given dimension is specified in both shape and
    shape_soft_constraint, shape takes precedence.
    """

    aspect_ratio: list[NonNegativeFloat] | None
    """Aspect ratio of the chunk shape.

    Specifies the relative chunk size along each dimension. The special value of 0 (or,
    equivalently, null) indicates no preference (which results in the default aspect
    ratio of 1 if not otherwise specified). The aspect ratio preference is only taken
    into account if the chunk size along a given dimension is not specified by shape or
    shape_soft_constraint, or otherwise constrained. For example, an aspect_ratio of [1,
    1.5, 1.5] indicates that the chunk size along dimensions 1 and 2 should be 1.5 times
    the chunk size along dimension 0. If the target number of elements is 486000, then
    the resultant chunk size will be [60, 90, 90] (assuming it is not otherwise constrai
    """

    aspect_ratio_soft_constraint: list[NonNegativeFloat] | None
    """Soft constraint on aspect ratio, lower precedence than `aspect_ratio`."""

    elements: PositiveInt | None
    """Preferred number of elements per chunk.

    Used in conjunction with aspect_ratio to determine the chunk size for dimensions
    that are not otherwise constrained. The special value of null indicates no
    preference, in which case a driver-specific default may be used.
    """

    elements_soft_constraint: PositiveInt | None
    """Preferred number of elements per chunk, lower precedence than `elements`."""


class ChunkLayout(TypedDict, total=False):
    """Driver-independent data storage layout for chunked storage formats.

    A chunk layout specifies a hierarchical regular grid with up to three levels:

    The write level, the top-most level, specifies the grid to which writes should be
    aligned. Writes of individual chunkss at this level may be performed without
    amplification. For the zarr Driver, n5 Driver and the neuroglancer_precomputed
    Driver using the unsharded format, the write level is also the only level; each
    write chunk corresponds to a single key in the underlying Key-Value Storage Layer.
    For the neuroglancer_precomputed Driver using the sharded format, each write chunk
    corresponds to an entire shard.

    The read level evenly subdivides write chunks by an additional regular grid. Reads
    of individual chunks at this level may be performed without amplification. Every
    write chunk boundary must be aligned to a read chunk boundary. If reads and writes
    may be performed at the same granularity, such as with the zarr Driver, n5 Driver,
    and the neuroglancer_precomputed Driver using the unsharded format, there is no
    additional read grid; a read chunk is the same size as a write chunk. For the
    neuroglancer_precomputed Driver using the sharded format, each read chunk
    corresponds to a base chunk as defined by the format.

    The codec level further subdivides the read level into codec chunks. For formats
    that make use of it, the codec chunk shape may affect the compression rate. For the
    neuroglancer_precomputed Driver when using the compressed segmentation encoding, the
    codec chunk shape specifies the compressed segmentation block shape. The codec block
    shape does not necessarily evenly subdivide the read chunk shape. (The precise
    offset of the codec chunk grid relative to the read chunk grid is not specified by
    the chunk layout.)
    """

    rank: int  # [0 - 32]
    """Number of dimensions.

    The rank is always a hard constraint. It is redundant to specify the rank if any
    other field that implicitly specifies the rank is included.
    """

    grid_origin: list[int] | None
    """Specifies hard constraints on the origin of the chunk grid.

    The length must equal the rank of the index space. Each element constrains the grid
    origin for the corresponding dimension. A value of null (or, equivalently,
    -9223372036854775808) indicates no constraint.
    """

    grid_origin_soft_constraint: list[int] | None
    """Specifies *preferred* values for the origin of the chunk grid.

    If a non-null value is specified for a given dimension in both
    grid_origin_soft_constraint and grid_origin, the value in grid_origin takes
    precedence.
    """

    inner_order: list[int]
    """Permutation specifying the element storage order within the innermost chunks.

    This must be a permutation of [0, 1, ..., rank-1]. Lexicographic order (i.e. C
    order/row-major order) is specified as [0, 1, ..., rank-1], while colexicographic
    order (i.e. Fortran order/column-major order) is specified as [rank-1, ..., 1, 0].
    """

    inner_order_soft_constraint: list[int]
    """Specifies a *preferred* value for inner_order rather than a hard constraint.

    If inner_order is also specified, it takes precedence.
    """

    write_chunk: ChunkLayoutGrid
    """Constraints on the chunk grid over which writes may be efficiently partitioned"""

    read_chunk: ChunkLayoutGrid
    """Constraints on the chunk grid over which reads may be efficiently partitioned"""

    codec_chunk: ChunkLayoutGrid
    """Constraints on the chunk grid used by the codec, if applicable."""

    chunk: ChunkLayoutGrid
    """Combined constraints on write/read/codec chunks.

    If `aspect_ratio` is specified, it applies to `write_chunk`, `read_chunk`, and
    `codec_chunk`. If `aspect_ratio_soft_constraint` is specified, it also applies to
    `write_chunk`, `read_chunk`, and `codec_chunk`, but with lower precedence than any
    write/read/codec-specific value that is also specified.

    If `shape` or `elements` is specified, it applies to `write_chunk` and `read_chunk`
    (but not `codec_chunk`). If `shape_soft_constraint` or `elements_soft_constraint` is
    specified, it also applies to `write_chunk` and `read_chunk`, but with lower
    precedence than any write/read-specific value that is also specified.
    """


class Codec(TypedDict, total=False):
    """Codecs are specified by a required driver property that identifies the driver.

    All other properties are driver-specific. Refer to the driver documentation for the
    supported codec drivers and the driver-specific properties.
    """

    # driver: Required[str]
    """Driver identifier

    Specifies the TensorStore driver to which this codec is applicable.
    """


Unit: TypeAlias = tuple[float, str] | str | float
"""Specifies a physical quantity/unit.

The quantity is specified as the combination of:

    - A numerical multiplier, represented as a double-precision floating-point number. A
      multiplier of 1 may be used to indicate a quanity equal to a single base unit.

    - A base_unit, represented as a string. An empty string may be used to indicate a
      dimensionless quantity. In general, TensorStore does not interpret the base unit
      string; some drivers impose additional constraints on the base unit, while other
      drivers may store the specified unit directly. It is recommended to follow the
      udunits2 syntax unless there is a specific need to deviate.

Three JSON formats are supported:

    - The canonical format, as a two-element [multiplier, base_unit] array. This format
      is always used by TensorStore when returning the JSON representation of a unit.

    - A single string. If the string contains a leading number, it is parsed as the
      multiplier and the remaining portion, after stripping leading and trailing
      whitespace, is used as the base_unit. If there is no leading number, the
      multiplier is 1 and the entire string, after stripping leading and trailing
      whitespace, is used as the base_unit.

    - A single number, to indicate a dimension-less unit with the specified multiplier.
"""


class Schema(TypedDict, total=False):
    """Specifies constraints on the schema.

    When opening an existing array, specifies constraints on the existing schema;
    opening will fail if the constraints do not match. Any soft constraints specified in
    the chunk_layout are ignored. When creating a new array, a suitable schema will be
    selected automatically based on the specified schema constraints in combination with
    any driver-specific constraints.
    """

    rank: int
    """Number of dimensions.

    The rank is always a hard constraint.
    """

    dtype: DType
    """Specifies the data type of the TensorStore.

    The data type is always a hard constraint.
    """

    domain: IndexDomain
    """Domain of the TensorStore, including bounds and optional dimension labels.

    The domain is always a hard constraint, except that a labeled dimension is allowed
    to match an unlabeled dimension, and an implicit, infinite bound is considered an
    unspecified bound and does not impose any constraints. When merging two schema
    constraint objects that both specify domains, any dimensions that are labeled in
    both domains must have the same label, and any explicit or finite bounds specified
    in both domains must be equal. If a dimension is labeled in one domain and unlabeled
    in the other, the label is retained. If a bound is implicit and infinite in one
    domain, the bound from the other domain is used.
    """

    chunk_layout: ChunkLayout
    """Data storage layout constraints.

    The rank of the chunk layout must match the rank of the schema. When merging schema
    constraints objects, the chunk layout constraints are merged recursively.
    """

    codec: Codec
    """Driver-specific compression and other parameters for encoding/decoding data.

    When merging schema constraints objects, the codec constraints are merged
    recursively.
    """

    fill_value: float | Any  # usually a float ... but I'm not sure if strictly
    """Fill value to use for missing data.

    The fill value data type must be convertible to the actual data type, and the shape
    must be broadcast-compatible with the domain.
    """

    dimension_units: list[Unit] | None
    """Physical units of each dimension.

    Specifies the physical quantity corresponding to an increment of 1 index along each
    dimension, i.e. the resolution. The length must match the rank of the schema.
    Specifying `None` for a dimension indicates that the unit is unknown.

    Example:
    `["4nm", "4nm", null]` specifies that the voxel size is 4nm along the first two
    dimensions, and unknown along the third dimension.
    """
