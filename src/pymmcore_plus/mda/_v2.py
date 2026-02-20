from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Empty, Full, Queue
from typing import TYPE_CHECKING, Any, Protocol, cast

from useq import MDASequence

from pymmcore_plus._logger import exceptions_logged, logger

from .events import PMDASignaler, _get_auto_MDA_callback_class

if TYPE_CHECKING:
    import numpy as np
    from useq import MDAEvent

    from ._engine import MDAEngine
    from ._protocol import PMDAEngine

    class SupportsLegacyOutput(Protocol):
        def frameReady(self, *args: Any) -> Any: ...

        def sequenceStarted(self, *args: Any) -> Any: ...

        def sequenceFinished(self, *args: Any) -> Any: ...


class RunStatus(str, Enum):
    """Status of a run from the perspective of the runner."""

    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class CriticalErrorPolicy(str, Enum):
    """Behavior when a critical callback raises during dispatch."""

    RAISE = "raise"
    CANCEL = "cancel"
    CONTINUE = "continue"


class NonCriticalErrorPolicy(str, Enum):
    """Behavior when a non-critical callback raises during dispatch."""

    LOG = "log"
    DISCONNECT = "disconnect"


class BackpressurePolicy(str, Enum):
    """Behavior when frame queues are full."""

    BLOCK = "block"
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    FAIL = "fail"


@dataclass(slots=True)
class RunPolicy:
    """Policy that controls callback failures and frame queue behavior."""

    critical_error: CriticalErrorPolicy = CriticalErrorPolicy.RAISE
    noncritical_error: NonCriticalErrorPolicy = NonCriticalErrorPolicy.LOG
    max_queue: int = 256
    backpressure: BackpressurePolicy = BackpressurePolicy.BLOCK
    observer_queue: int = 256


@dataclass(slots=True)
class ConsumerReport:
    """Per-consumer dispatch summary."""

    name: str
    submitted: int = 0
    processed: int = 0
    dropped: int = 0
    errors: list[Exception] = field(default_factory=list)


@dataclass(slots=True)
class RunReport:
    """Summary of a run used for diagnostics and observability."""

    status: RunStatus
    started_at: float
    finished_at: float
    consumer_reports: tuple[ConsumerReport, ...]


class FrameConsumer(Protocol):
    """Unified callback protocol with name-defined criticality semantics."""

    def setup_sequence(
        self, sequence: MDASequence, summary_meta: dict[str, Any]
    ) -> None: ...

    def receive_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None: ...

    def finish_sequence(self, sequence: MDASequence, status: RunStatus) -> None: ...

    def on_start(self, sequence: MDASequence, summary_meta: dict[str, Any]) -> None: ...

    def on_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None: ...

    def on_finish(self, sequence: MDASequence, status: RunStatus) -> None: ...


if TYPE_CHECKING:
    from typing import TypeAlias

    OutputTarget: TypeAlias = Path | str | FrameConsumer | SupportsLegacyOutput
else:
    OutputTarget = Any


@dataclass(slots=True)
class ConsumerSpec:
    """Registration info for a consumer."""

    name: str
    consumer: FrameConsumer


@dataclass(slots=True)
class _FrameMessage:
    frame: np.ndarray
    event: MDAEvent
    meta: dict[str, Any]


class ConsumerDispatchError(RuntimeError):
    """Raised when a critical consumer fails and policy requests propagation."""

    def __init__(self, consumer_name: str, error: Exception) -> None:
        super().__init__(f"Consumer callback {consumer_name!r} failed: {error}")
        self.consumer_name = consumer_name
        self.error = error


def _callback(consumer: FrameConsumer, name: str) -> Callable[..., None] | None:
    callback = getattr(consumer, name, None)
    if callable(callback):
        return cast("Callable[..., None]", callback)
    return None


@dataclass(slots=True)
class _FrameEndpoint:
    name: str
    callback: Callable[..., None]
    critical: bool


@dataclass(slots=True)
class _LifecycleEndpoint:
    name: str
    callback: Callable[..., None]
    critical: bool


class _ConsumerWorker:
    """Threaded worker dedicated to one frame callback endpoint."""

    _STOP = object()

    def __init__(self, endpoint: _FrameEndpoint, policy: RunPolicy) -> None:
        self.name = endpoint.name
        self.callback = endpoint.callback
        self.critical = endpoint.critical
        self.policy = policy
        queue_size = policy.max_queue
        if not self.critical:
            queue_size = policy.observer_queue

        self.queue: Queue[_FrameMessage | object] = Queue(maxsize=queue_size)
        self.thread = threading.Thread(
            target=self._run, name=f"mda-consumer-{self.name}"
        )
        self.report: ConsumerReport | None = None
        if self.critical:
            self.report = ConsumerReport(name=self.name)
        self._fatal_error: ConsumerDispatchError | None = None
        self._stop_requested = threading.Event()
        self._disconnected = threading.Event()

    def start(self) -> None:
        self.thread.start()

    def submit(self, message: _FrameMessage) -> bool:
        if self._disconnected.is_set():
            return False

        if not self.critical:
            try:
                self.queue.put_nowait(message)
                return True
            except Full:
                return False

        assert self.report is not None
        self.report.submitted += 1
        if self.policy.backpressure is BackpressurePolicy.BLOCK:
            self.queue.put(message)
            return True

        if self.policy.backpressure is BackpressurePolicy.FAIL:
            try:
                self.queue.put_nowait(message)
            except Full as err:
                raise BufferError(f"Consumer queue is full for {self.name!r}") from err
            return True

        if self.policy.backpressure is BackpressurePolicy.DROP_NEWEST:
            try:
                self.queue.put_nowait(message)
                return True
            except Full:
                self.report.dropped += 1
                return False

        if self.policy.backpressure is BackpressurePolicy.DROP_OLDEST:
            try:
                self.queue.put_nowait(message)
                return True
            except Full:
                try:
                    _ = self.queue.get_nowait()
                except Empty:
                    self.report.dropped += 1
                    return False
                try:
                    self.queue.put_nowait(message)
                    self.report.dropped += 1
                    return True
                except Full:
                    self.report.dropped += 1
                    return False

        return False

    def stop(self) -> None:
        self.queue.put(self._STOP)

    def join(self) -> None:
        if self.thread.is_alive():
            self.thread.join()

    @property
    def fatal_error(self) -> ConsumerDispatchError | None:
        return self._fatal_error

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested.is_set()

    def _run(self) -> None:
        while True:
            item = self.queue.get()
            if item is self._STOP:
                return
            assert isinstance(item, _FrameMessage)
            try:
                self.callback(item.frame, item.event, item.meta)
                if self.report is not None:
                    self.report.processed += 1
            except Exception as err:
                if not self.critical:
                    if self.policy.noncritical_error is NonCriticalErrorPolicy.LOG:
                        logger.exception("Non-critical frame callback failed")
                        continue
                    if (
                        self.policy.noncritical_error
                        is NonCriticalErrorPolicy.DISCONNECT
                    ):
                        self._disconnected.set()
                        return

                assert self.report is not None
                self.report.errors.append(err)
                if self.policy.critical_error is CriticalErrorPolicy.CONTINUE:
                    continue

                self._fatal_error = ConsumerDispatchError(self.name, err)
                self._stop_requested.set()
                return


class FrameDispatcher:
    """Bounded, threaded dispatcher for critical and non-critical callbacks."""

    def __init__(self, policy: RunPolicy | None = None) -> None:
        self.policy = policy or RunPolicy()
        self._specs: list[ConsumerSpec] = []
        self._workers: list[_ConsumerWorker] = []
        self._lifecycle_endpoints: list[_LifecycleEndpoint] = []
        self._started_at: float = 0.0
        self._finished_at: float = 0.0

    def add_consumer(self, spec: ConsumerSpec) -> None:
        """Register a consumer with name-defined callback semantics."""
        self._specs.append(spec)

    def start(self, sequence: MDASequence, summary_meta: dict[str, Any]) -> None:
        """Start workers and deliver start lifecycle callbacks synchronously."""
        self._started_at = time.perf_counter()

        frame_endpoints: list[_FrameEndpoint] = []
        lifecycle_endpoints: list[_LifecycleEndpoint] = []
        for spec in self._specs:
            critical_start = _callback(spec.consumer, "setup_sequence")
            noncritical_start = _callback(spec.consumer, "on_start")
            critical_finish = _callback(spec.consumer, "finish_sequence")
            noncritical_finish = _callback(spec.consumer, "on_finish")
            critical_frame = _callback(spec.consumer, "receive_frame")
            noncritical_frame = _callback(spec.consumer, "on_frame")

            include_critical = True
            include_noncritical = True
            if critical_start is not None:
                include_critical = self._invoke_lifecycle(
                    _LifecycleEndpoint(
                        name=f"{spec.name}.setup_sequence",
                        callback=critical_start,
                        critical=True,
                    ),
                    sequence,
                    summary_meta,
                )
            if noncritical_start is not None:
                include_noncritical = self._invoke_lifecycle(
                    _LifecycleEndpoint(
                        name=f"{spec.name}.on_start",
                        callback=noncritical_start,
                        critical=False,
                    ),
                    sequence,
                    summary_meta,
                )

            if include_critical:
                if critical_frame is not None:
                    frame_endpoints.append(
                        _FrameEndpoint(
                            name=f"{spec.name}.receive_frame",
                            callback=critical_frame,
                            critical=True,
                        )
                    )
                if critical_finish is not None:
                    lifecycle_endpoints.append(
                        _LifecycleEndpoint(
                            name=f"{spec.name}.finish_sequence",
                            callback=critical_finish,
                            critical=True,
                        )
                    )

            if include_noncritical:
                if noncritical_frame is not None:
                    frame_endpoints.append(
                        _FrameEndpoint(
                            name=f"{spec.name}.on_frame",
                            callback=noncritical_frame,
                            critical=False,
                        )
                    )
                if noncritical_finish is not None:
                    lifecycle_endpoints.append(
                        _LifecycleEndpoint(
                            name=f"{spec.name}.on_finish",
                            callback=noncritical_finish,
                            critical=False,
                        )
                    )

        self._lifecycle_endpoints = lifecycle_endpoints
        self._workers = [
            _ConsumerWorker(endpoint, self.policy) for endpoint in frame_endpoints
        ]
        for worker in self._workers:
            worker.start()

    def submit(self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]) -> None:
        """Submit one frame to registered frame callbacks."""
        msg = _FrameMessage(frame, event, meta)
        for worker in self._workers:
            worker.submit(msg)

    def should_cancel(self) -> bool:
        """Return whether a critical consumer requested cancellation."""
        return any(worker.stop_requested for worker in self._workers)

    def close(self, sequence: MDASequence, status: RunStatus) -> RunReport:
        """Stop workers, run finish lifecycle callbacks, and return a report."""
        for worker in self._workers:
            worker.stop()
        for worker in self._workers:
            worker.join()

        for endpoint in self._lifecycle_endpoints:
            self._invoke_lifecycle(endpoint, sequence, status)

        self._finished_at = time.perf_counter()

        fatal = next((w.fatal_error for w in self._workers if w.fatal_error), None)
        if fatal and self.policy.critical_error is CriticalErrorPolicy.RAISE:
            raise fatal

        return RunReport(
            status=status,
            started_at=self._started_at,
            finished_at=self._finished_at,
            consumer_reports=tuple(
                worker.report for worker in self._workers if worker.report is not None
            ),
        )

    def _invoke_lifecycle(self, endpoint: _LifecycleEndpoint, *args: Any) -> bool:
        try:
            endpoint.callback(*args)
        except Exception as err:
            if not endpoint.critical:
                if self.policy.noncritical_error is NonCriticalErrorPolicy.LOG:
                    logger.exception(
                        "Non-critical lifecycle callback failed: %s", endpoint.name
                    )
                    return True
                if self.policy.noncritical_error is NonCriticalErrorPolicy.DISCONNECT:
                    return False
                return True

            if self.policy.critical_error is CriticalErrorPolicy.CONTINUE:
                return True
            if self.policy.critical_error is CriticalErrorPolicy.CANCEL:
                return False
            raise ConsumerDispatchError(endpoint.name, err) from err

        return True


@dataclass(slots=True)
class _FrameReadySignalConsumer:
    """Non-critical consumer relaying frames to `MDARunnerV2.events.frameReady`."""

    events: PMDASignaler

    def setup_sequence(
        self, sequence: MDASequence, summary_meta: dict[str, Any]
    ) -> None:
        del sequence, summary_meta

    def receive_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        del frame, event, meta

    def finish_sequence(self, sequence: MDASequence, status: RunStatus) -> None:
        del sequence, status

    def on_start(self, sequence: MDASequence, summary_meta: dict[str, Any]) -> None:
        del sequence, summary_meta

    def on_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        with exceptions_logged():
            self.events.frameReady.emit(frame, event, meta)

    def on_finish(self, sequence: MDASequence, status: RunStatus) -> None:
        del sequence, status


class _LegacyOutputAdapter:
    """Adapt legacy handlers (`frameReady`, `sequenceStarted`, ...) to consumer API."""

    def __init__(self, handler: SupportsLegacyOutput) -> None:
        self._handler = handler

    def setup_sequence(
        self, sequence: MDASequence, summary_meta: dict[str, Any]
    ) -> None:
        callback = getattr(self._handler, "sequenceStarted", None)
        if callable(callback):
            try:
                callback(sequence, summary_meta)
            except TypeError:
                callback(sequence)

    def receive_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        callback = getattr(self._handler, "frameReady", None)
        if not callable(callback):
            raise TypeError("Legacy output does not provide callable frameReady")

        try:
            callback(frame, event, meta)
        except TypeError:
            try:
                callback(frame, event)
            except TypeError:
                try:
                    callback(frame)
                except TypeError:
                    callback()

    def finish_sequence(self, sequence: MDASequence, status: RunStatus) -> None:
        callback = getattr(self._handler, "sequenceFinished", None)
        if callable(callback):
            callback(sequence)
        _ = status

    def on_start(self, sequence: MDASequence, summary_meta: dict[str, Any]) -> None:
        del sequence, summary_meta

    def on_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        del frame, event, meta

    def on_finish(self, sequence: MDASequence, status: RunStatus) -> None:
        del sequence, status


class MDARunnerV2:
    """Experimental MDA runner with name-defined callback semantics."""

    def __init__(self) -> None:
        self._engine: PMDAEngine | None = None
        self._signals = _get_auto_MDA_callback_class()()
        self._running = False
        self._paused = False
        self._paused_time: float = 0
        self._pause_interval: float = 0.1
        self._canceled = False
        self._sequence: MDASequence | None = None
        self._sequence_t0: float = 0.0
        self._t0: float = 0.0
        self._last_report: RunReport | None = None

    def set_engine(self, engine: PMDAEngine) -> PMDAEngine | None:
        """Set the PMDAEngine for this runner."""
        old_engine, self._engine = self._engine, engine
        return old_engine

    @property
    def engine(self) -> MDAEngine | None:
        """Return the currently configured engine."""
        return self._engine  # type: ignore[return-value]

    @property
    def events(self) -> PMDASignaler:
        """Signals emitted during the MDA run."""
        return self._signals

    @property
    def last_report(self) -> RunReport | None:
        """Return the latest run report if available."""
        return self._last_report

    def is_running(self) -> bool:
        """Return whether an acquisition is currently underway."""
        return self._running

    def is_paused(self) -> bool:
        """Return whether the acquisition is currently paused."""
        return self._paused

    def cancel(self) -> None:
        """Cancel the currently running acquisition."""
        self._canceled = True
        self._paused_time = 0

    def toggle_pause(self) -> None:
        """Toggle the paused state of the current acquisition."""
        if self._running:
            self._paused = not self._paused
            self._signals.sequencePauseToggled.emit(self._paused)

    def seconds_elapsed(self) -> float:
        """Return seconds elapsed since the sequence started."""
        return time.perf_counter() - self._sequence_t0

    def event_seconds_elapsed(self) -> float:
        """Return seconds elapsed on the event timer."""
        return time.perf_counter() - self._t0

    def run(
        self,
        events: Iterable[MDAEvent],
        *,
        consumers: Sequence[ConsumerSpec] = (),
        output: OutputTarget | Sequence[OutputTarget] | None = None,
        policy: RunPolicy | None = None,
    ) -> RunReport:
        """Run the MDA using explicit consumer registrations."""
        if self._engine is None:
            raise RuntimeError("No MDAEngine set.")

        sequence = events if isinstance(events, MDASequence) else MDASequence()
        dispatcher = FrameDispatcher(policy)
        dispatcher.add_consumer(
            ConsumerSpec(
                name="frameReady-signal-observer",
                consumer=_FrameReadySignalConsumer(self._signals),
            )
        )

        for spec in consumers:
            dispatcher.add_consumer(spec)

        for spec in self._coerce_outputs(output):
            dispatcher.add_consumer(spec)

        error: Exception | None = None
        status = RunStatus.COMPLETED

        try:
            summary_meta = self._prepare_to_run(sequence)
            dispatcher.start(sequence, summary_meta)
            self._run_loop(dispatcher, events)
            if self._canceled:
                status = RunStatus.CANCELED
        except Exception as exc:
            status = RunStatus.FAILED
            error = exc
        finally:
            with exceptions_logged():
                self._finish_run(sequence)

        report = dispatcher.close(sequence, status)
        self._last_report = report

        if error is not None:
            raise error
        return report

    def _coerce_outputs(
        self, output: OutputTarget | Sequence[OutputTarget] | None
    ) -> list[ConsumerSpec]:
        if output is None:
            return []

        if isinstance(output, (str, Path)) or not isinstance(output, Sequence):
            items: Sequence[OutputTarget] = [output]
        else:
            items = output

        specs: list[ConsumerSpec] = []
        for index, item in enumerate(items):
            if isinstance(item, (str, Path)):
                specs.append(
                    ConsumerSpec(
                        name=f"output{index}",
                        consumer=self._consumer_for_path(item),
                    )
                )
                continue

            receive_frame = getattr(item, "receive_frame", None)
            if callable(receive_frame):
                specs.append(
                    ConsumerSpec(
                        name=f"output{index}",
                        consumer=cast("FrameConsumer", item),
                    )
                )
                continue

            frame_ready = getattr(item, "frameReady", None)
            if callable(frame_ready):
                specs.append(
                    ConsumerSpec(
                        name=f"output{index}",
                        consumer=_LegacyOutputAdapter(
                            cast("SupportsLegacyOutput", item)
                        ),
                    )
                )
                continue

            raise TypeError(f"Invalid output object: {item!r}")

        return specs

    def _consumer_for_path(self, path: str | Path) -> FrameConsumer:
        from pymmcore_plus.mda.handlers import handler_for_path

        handler = cast("SupportsLegacyOutput", handler_for_path(path))
        return _LegacyOutputAdapter(handler)

    def _run_loop(
        self, dispatcher: FrameDispatcher, events: Iterable[MDAEvent]
    ) -> None:
        assert self._engine is not None
        teardown_event = getattr(self._engine, "teardown_event", lambda e: None)
        if isinstance(events, Iterator):
            event_iterator = iter
        else:
            event_iterator = getattr(self._engine, "event_iterator", iter)
        _events: Iterator[MDAEvent] = event_iterator(events)

        self._reset_event_timer()
        self._sequence_t0 = self._t0

        for event in _events:
            if event.reset_event_timer:
                self._reset_event_timer()
            if self._wait_until_event(event) or not self._running:
                break

            self._signals.eventStarted.emit(event)
            self._engine.setup_event(event)

            try:
                runner_time_ms = self.seconds_elapsed() * 1000
                event.metadata["runner_t0"] = self._sequence_t0
                output = self._engine.exec_event(event) or ()
                for payload in output:
                    img, payload_event, meta = payload
                    payload_event.metadata.pop("runner_t0", None)
                    if "runner_time_ms" not in meta:
                        meta["runner_time_ms"] = runner_time_ms
                    dispatcher.submit(img, payload_event, cast("dict[str, Any]", meta))
                    if dispatcher.should_cancel():
                        self._canceled = True
                        break
            finally:
                teardown_event(event)

            if self._canceled:
                break

    def _prepare_to_run(self, sequence: MDASequence) -> dict[str, Any]:
        if self._engine is None:
            raise RuntimeError("No MDAEngine set.")

        self._running = True
        self._paused = False
        self._paused_time = 0.0
        self._sequence = sequence

        meta = self._engine.setup_sequence(sequence) or {}
        self._signals.sequenceStarted.emit(sequence, meta)
        return cast("dict[str, Any]", meta)

    def _finish_run(self, sequence: MDASequence) -> None:
        self._running = False
        self._canceled = False

        if hasattr(self._engine, "teardown_sequence"):
            self._engine.teardown_sequence(sequence)  # type: ignore[union-attr]

        self._signals.sequenceFinished.emit(sequence)

    def _reset_event_timer(self) -> None:
        self._t0 = time.perf_counter()

    def _check_canceled(self) -> bool:
        if self._canceled:
            self._signals.sequenceCanceled.emit(self._sequence)
            return True
        return False

    def _wait_until_event(self, event: MDAEvent) -> bool:
        if not self._running:
            return False
        if self._check_canceled():
            return True

        while self._paused and not self._canceled:
            self._paused_time += self._pause_interval
            time.sleep(self._pause_interval)

            if self._check_canceled():
                return True

        if event.min_start_time:
            go_at = event.min_start_time + self._paused_time
            remaining_wait_time = go_at - self.event_seconds_elapsed()
            while remaining_wait_time > 0:
                self._signals.awaitingEvent.emit(event, remaining_wait_time)
                while self._paused and not self._canceled:
                    self._paused_time += self._pause_interval
                    remaining_wait_time += self._pause_interval
                    time.sleep(self._pause_interval)

                if self._canceled:
                    break

                time.sleep(min(remaining_wait_time, 0.5))
                remaining_wait_time = go_at - self.event_seconds_elapsed()

        return self._check_canceled()
