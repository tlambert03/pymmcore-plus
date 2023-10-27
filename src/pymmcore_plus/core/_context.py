from __future__ import annotations

from contextlib import contextmanager
from typing import Any, ChainMap, Iterator, MutableMapping

from psygnal import Signal

_NULL = object()


class Context(ChainMap):
    """Evented Mapping of keys to values."""

    changed = Signal(set)  # Set[str]

    def __init__(self, *maps: MutableMapping) -> None:
        super().__init__(*maps)
        for m in maps:
            if isinstance(m, Context):
                m.changed.connect(self.changed)

    @contextmanager
    def buffered_changes(self) -> Iterator[None]:
        """Context in which to accumulated changes before emitting."""
        with self.changed.paused(lambda a, b: (a[0].union(b[0]),)):
            yield

    def __setitem__(self, k: str, v: Any) -> None:
        emit = self.get(k, _NULL) is not v
        super().__setitem__(k, v)
        if emit:
            self.changed.emit({k})

    def __delitem__(self, k: str) -> None:
        emit = k in self
        super().__delitem__(k)
        if emit:
            self.changed.emit({k})

    def new_child(self, m: MutableMapping | None = None) -> Context:
        """Create a new child context from this one."""
        new = super().new_child(m=m)
        self.changed.connect(new.changed)
        return new

    def __hash__(self) -> int:
        return id(self)
