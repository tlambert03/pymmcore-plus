import warnings
from collections.abc import Iterator

from useq import MDASequence

MSG = (
    "This sequence is a placeholder for a generator of events with unknown "
    "length & shape. Iterating over it has no effect."
)


class GeneratorMDASequence(MDASequence):
    """Placeholder sequence used when the runner is given events, not an `MDASequence`.

    When [`MDARunner.run`][pymmcore_plus.mda.MDARunner.run] receives any iterable of
    events other than a [`useq.MDASequence`][] (a list, a generator, a queue-backed
    iterator, a `useq.v2.MDASequence`, etc...), the shape of the experiment isn't
    known in advance.  An empty `GeneratorMDASequence` is then passed to the
    engine's `setup_sequence` and emitted in `sequenceStarted` in its place.
    """

    axis_order: tuple[str, ...] = ()

    @property
    def sizes(self) -> dict[str, int]:  # pragma: no cover
        warnings.warn(MSG, stacklevel=2)
        return {}

    def iter_axis(self, axis: str) -> Iterator:  # pragma: no cover
        warnings.warn(MSG, stacklevel=2)
        yield from []

    def __str__(self) -> str:
        return "GeneratorMDASequence()"
