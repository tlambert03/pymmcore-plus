from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Required, TypeAlias, Unpack


class Context(TypedDict, total=False): ...


class IndexTransform(TypedDict, total=False): ...


class IndexDomain(TypedDict, total=False): ...


class ChunkLayout(TypedDict, total=False): ...


class Codec(TypedDict, total=False):
    """Codecs are specified by a required driver property that identifies the driver.

    All other properties are driver-specific. Refer to the driver documentation for the
    supported codec drivers and the driver-specific properties.
    """


DType: TypeAlias = Literal[
    "bool",
    "char",
    "byte",
    "int4",
    "int8",
    "uint8",
    "int16",
    "uint16",
    "int32",
    "uint32",
    "int64",
    "uint64",
    "float8_e4m3fn",
    "float8_e4m3fnuz",
    "float8_e4m3b11fnuz",
    "float8_e5m2",
    "float8_e5m2fnuz",
    "float16",
    "bfloat16",
    "float32",
    "float64",
    "complex64",
    "complex128",
    "string",
    "ustring",
    "json",
]


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


class _TensorStoreSpec(TypedDict, total=False):
    """Specifies a TensorStore to open/create."""

    # driver: Required[str]
    """Driver identifier"""
    context: Context | None
    """Specifies context resources that augment/override the parent context."""
    dtype: DType
    """Specifies the data type."""
    rank: int
    """Specifies the rank of the TensorStore.

    If transform is also specified, the input rank must match. Otherwise, the rank
    constraint applies to the driver directly.
    """
    transform: IndexTransform
    """Specifies a transform."""
    schema: Schema
    """Specifies constraints on the schema.

    When opening an existing array, specifies constraints on the existing schema;
    opening will fail if the constraints do not match. Any soft constraints specified in
    the chunk_layout are ignored. When creating a new array, a suitable schema will be
    selected automatically based on the specified schema constraints in combination with
    any driver-specific constraints.
    """


KvStoreUrl = str  #  file:// | gs:// | http:// and https:// | memory:// | s3://


class KvStore(TypedDict, total=False):
    """Key-value store specification."""

    driver: Required[str]
    path: str
    context: Context


ContextResource: TypeAlias = dict | bool | float | int | str | None
CacheRevalidationBound: TypeAlias = bool | Literal["open"] | int


class _KeyValueStoreBackedChunkDriverSpec(_TensorStoreSpec, total=False):
    """Common options supported by all chunked storage drivers."""

    # driver: Required[Literal["n5", "neuroglancer_precomputed", "zarr", "zarr3"]]
    kvstore: KvStore | KvStoreUrl
    """Specifies the underlying storage mechanism."""
    path: str
    """Additional path within the KvStore specified by kvstore.

    This is joined as an additional "/"-separated path component after any path member
    directly within kvstore. This is supported for backwards compatibility only; the
    KvStore.path member should be used instead.

    Example: "path/to/data"
    """
    open: bool
    """Open an existing TensorStore.

    If neither open nor create is specified, defaults to true.
    """
    create: bool  # default: True
    """Create a new TensorStore.

    Specify true for both open and create to permit either opening an existing
    TensorStore or creating a new TensorStore if it does not already exist.
    """
    delete_existing: bool  # default: False
    """Delete any existing data at the specified path before creating a new TensorStore.

    Requires that create is true, and that open is false.
    """
    assume_metadata: bool  # default: False
    """
    Neither read nor write stored metadata. Instead, just assume any necessary metadata
    based on constraints in the spec, using the same defaults for any unspecified
    metadata as when creating a new TensorStore. The stored metadata need not even
    exist. Operations such as resizing that modify the stored metadata are not
    supported. Requires that open is true and delete_existing is false. This option
    takes precedence over assume_cached_metadata if that option is also specified.
    """
    assume_cached_metadata: bool  # default: False
    """
    Skip reading the metadata when opening. Instead, just assume any necessary metadata
    based on constraints in the spec, using the same defaults for any unspecified
    metadata as when creating a new TensorStore. The stored metadata may still be
    accessed by subsequent operations that need to re-validate or modify the metadata.
    Requires that open is true and delete_existing is false. The assume_metadata option
    takes precedence if also specified.

    Warning: This option can lead to data corruption if the assumed metadata does not
    match the stored metadata, or multiple concurrent writers use different assumed
    metadata.
    """
    cache_pool: ContextResource  # default: "cache_pool"
    """Cache pool for data.

    Specifies or references a previously defined Context.cache_pool. It is normally more
    convenient to specify a default cache_pool in the context.
    """
    metadata_cache_pool: ContextResource
    """Cache pool for metadata only.

    Specifies or references a previously defined Context.cache_pool. If not specified,
    defaults to the value of cache_pool.
    """
    data_copy_concurrency: ContextResource  # default: "data_copy_concurrency"
    """Specifies or references a previously defined Context.data_copy_concurrency.

    It is normally more convenient to specify a default data_copy_concurrency in the
    context.
    """
    recheck_cached_metadata: CacheRevalidationBound  # default: "open"
    """Time after which cached metadata is assumed to be fresh.

    Cached metadata older than the specified time is revalidated prior to use. The
    metadata is used to check the bounds of every read or write operation.

    Specifying true means that the metadata will be revalidated prior to every read or
    write operation. With the default value of "open", any cached metadata is
    revalidated when the TensorStore is opened but is not rechecked for each read or
    write operation.
    """
    recheck_cached_data: CacheRevalidationBound  # default: True
    """Time after which cached data is assumed to be fresh.

    Cached data older than the specified time is revalidated prior to being returned
    from a read operation. Partial chunk writes are always consistent regardless of the
    value of this option.

    The default value of true means that cached data is revalidated on every read. To
    enable in-memory data caching, you must both specify a cache_pool with a non-zero
    total_bytes_limit and also specify false, "open", or an explicit time bound for
    recheck_cached_data.
    """
    fill_missing_data_reads: bool  # default: True
    """Replace missing chunks with the fill value when reading.

    If disabled, reading a missing chunk will result in an error. Note that the fill
    value may still be used when writing a partial chunk. Typically this should only be
    set to false in the case that store_data_equal_to_fill_value was enabled when
    writing.
    """
    store_data_equal_to_fill_value: bool  # default: False
    """Store all explicitly written data, even if it is equal to the fill value.

    This ensures that explicitly written data, even if it is equal to the fill value,
    can be distinguished from missing data. If disabled, chunks equal to the fill value
    may be represented as missing chunks.
    """


Zarr3DataType: TypeAlias = Literal[
    "bool",
    "int4",
    "int8",
    "uint8",
    "int16",
    "uint16",
    "int32",
    "uint32",
    "int64",
    "uint64",
    "float16",
    "bfloat16",
    "float32",
    "float64",
    "complex64",
    "complex128",
]


class Zarr3Metadata(TypedDict, total=False):
    """Zarr v3 array metadata.

    Specifies constraints on the metadata, as in the zarr.json metadata file, except
    that all members are optional and codecs may be left partially-specified, in which
    case default options are chosen automatically. When creating a new array, the new
    metadata is obtained by combining these metadata constraints with any Schema
    constraints.
    """

    zarr_format: Literal[3]
    """Identifies the Zarr specification version."""
    node_type: Literal["array"]
    """Identifies the Zarr node type."""
    shape: Sequence[int]  # MAY be required
    """Dimensions of the array.

    Required when creating a new array if the Schema.domain is not otherwise specified.
    """
    data_type: Zarr3DataType
    """Data type of the array."""


class Zarr3DriverKwargs(_KeyValueStoreBackedChunkDriverSpec, total=False):
    """Zarr v3 is a chunked array storage format.

    The zarr3 driver provides access to Zarr v3-format arrays backed by any supported
    Key-Value Storage Layer. It supports reading, writing, creating new arrays, and
    resizing arrays.
    """

    metadata: Zarr3Metadata


class Zarr3DriverSpec(Zarr3DriverKwargs, total=False):
    """Complete Zarr3 driver spec."""

    driver: Required[Literal["zarr3"]]


TensorStoreSpec = (
    Zarr3DriverSpec,
    # ...
)


def zarr3_create(
    shape: Sequence[int],
    **kwargs: Unpack[Zarr3DriverKwargs],
) -> ts.Future[ts.TensorStore]:
    """Create a new Zarr3 TensorStore."""
    kvstore: KvStore | KvStoreUrl
    if path := kwargs.pop("path", None):
        if "://" in str(path):
            kvstore = str(path)
        else:
            path = str(Path(path).expanduser().resolve())
            kvstore = {"driver": "file", "path": str(path)}
    else:
        kvstore = "memory://"

    spec: Zarr3DriverSpec = {
        "driver": "zarr3",
        "kvstore": kvstore,
        "create": True,
        "dtype": "float32",
        "metadata": {"shape": shape},
        **kwargs,
    }
    return ts.open(spec)


if __name__ == "__main__":
    import tensorstore as ts

    print(
        zarr3_create(
            (4, 20, 20), path="~/Desktop/thing.zarr", delete_existing=True
        ).result()
    )
