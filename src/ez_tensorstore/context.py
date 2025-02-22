"""Resource context for TensorStore drivers.

Configuration options for TensorStore drivers are specified using a context
framework, which allows resources such as cache pools, concurrent execution pools,
and authentication credentials to be specified using JSON in a way that allows
sharing of resources by multiple TensorStore drivers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

if TYPE_CHECKING:
    from .schema import NonNegativeInt, PositiveInt

DirectResourceSpecifier: TypeAlias = object | bool | float
"""Specifies the resource directly.

Any constraints on the value are determined by the particular <resource-type>.
"""

NamedResourceSpecifier: TypeAlias = str
"""References another resource of the same type in the current or parent context.

Use the syntax "<resource-type>" or "<resource-type>#<id>", where <resource-type>
matches the type of this resource.
"""

NullSpecifier: TypeAlias = None
"""Specifies a new instance of the default resource of the given <resource-type>.

Only valid within a Context specification.
"""


ContextResource: TypeAlias = (
    DirectResourceSpecifier | NamedResourceSpecifier | NullSpecifier
)
"""Specifies a context resource of a particular <resource-type>."""

# ---------------------------- Context --------------------------

Context: TypeAlias = Mapping[str, ContextResource]
"""Mapping of resource identifiers to ContextResource specifications.

Example:
{
  "cache_pool": {"total_bytes_limit": 10000000},
  "cache_pool#remote": {"total_bytes_limit": 100000000},
  "data_copy_concurrency": {"limit": 8}
}
"""

# ---------------------------- Special ContextResource Types --------------------------


# key 'cache_pool' in a Context
class ContextCachePool(TypedDict, total=False):
    """Specifies the size of an in-memory Least Recently Used (LRU) cache.

    Each cache_pool resource specifies a separate memory pool.
    """

    total_bytes_limit: NonNegativeInt


# key 'data_copy_concurrency' in a Context
class ContextDataCopyConcurrency(TypedDict, total=False):
    """Specifies a limit on the number of CPU cores...

    used concurrently for data copying/encoding/decoding.
    """

    limit: PositiveInt | Literal["shared"]
    """The maximum number of CPU cores that may be used.

    If the special value of "shared" is specified, a shared global limit equal to the
    number of CPU cores/threads available applies.
    """
