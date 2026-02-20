from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
from useq import MDAEvent, MDASequence

from pymmcore_plus.mda import (
    ConsumerSpec,
    CriticalErrorPolicy,
    FrameDispatcher,
    NonCriticalErrorPolicy,
    RunPolicy,
    RunStatus,
)
from pymmcore_plus.mda._v2 import BackpressurePolicy, ConsumerDispatchError

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


class RecordingSink:
    def __init__(self) -> None:
        self.started = False
        self.finished = False
        self.frames = 0

    def setup_sequence(
        self, sequence: MDASequence, summary_meta: dict[str, Any]
    ) -> None:
        self.started = True

    def receive_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        self.frames += 1

    def finish_sequence(self, sequence: MDASequence, status: RunStatus) -> None:
        self.finished = True


class SlowSink(RecordingSink):
    def receive_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        time.sleep(0.02)
        super().receive_frame(frame, event, meta)


class FailingSink(RecordingSink):
    def receive_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        raise RuntimeError("sink boom")


class FailingObserver:
    def __init__(self) -> None:
        self.calls = 0

    def on_start(self, sequence: MDASequence, summary_meta: dict[str, Any]) -> None:
        del sequence, summary_meta

    def on_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
    ) -> None:
        self.calls += 1
        del frame, event, meta
        raise RuntimeError("observer boom")

    def on_finish(self, sequence: MDASequence, status: RunStatus) -> None:
        del sequence, status


def _payload(i: int) -> tuple[np.ndarray, MDAEvent, dict[str, Any]]:
    event = MDAEvent.model_validate({"index": {"t": i}})
    return np.zeros((4, 4), dtype=np.uint16), event, {}


def test_frame_dispatcher_lifecycle() -> None:
    sequence = MDASequence.model_validate({"time_plan": {"loops": 2, "interval": 0}})
    sink = RecordingSink()
    dispatcher = FrameDispatcher(RunPolicy(max_queue=8))
    dispatcher.add_consumer(ConsumerSpec(name="rec", consumer=sink))

    dispatcher.start(sequence, {})
    for i in range(4):
        dispatcher.submit(*_payload(i))
    report = dispatcher.close(sequence, RunStatus.COMPLETED)

    assert sink.started
    assert sink.finished
    assert sink.frames == 4
    assert report.status is RunStatus.COMPLETED
    assert report.consumer_reports[0].processed == 4


def test_frame_dispatcher_sink_error_raises() -> None:
    sequence = MDASequence()
    dispatcher = FrameDispatcher(
        RunPolicy(
            critical_error=CriticalErrorPolicy.RAISE,
            backpressure=BackpressurePolicy.BLOCK,
            max_queue=8,
        )
    )
    dispatcher.add_consumer(ConsumerSpec(name="bad", consumer=FailingSink()))

    dispatcher.start(sequence, {})
    dispatcher.submit(*_payload(0))

    with pytest.raises(ConsumerDispatchError):
        dispatcher.close(sequence, RunStatus.FAILED)


def test_frame_dispatcher_backpressure_drop_newest() -> None:
    sequence = MDASequence()
    sink = SlowSink()
    dispatcher = FrameDispatcher(
        RunPolicy(
            max_queue=1,
            backpressure=BackpressurePolicy.DROP_NEWEST,
            critical_error=CriticalErrorPolicy.CONTINUE,
        )
    )
    dispatcher.add_consumer(ConsumerSpec(name="slow", consumer=sink))

    dispatcher.start(sequence, {})
    for i in range(30):
        dispatcher.submit(*_payload(i))
    report = dispatcher.close(sequence, RunStatus.COMPLETED)

    consumer_report = report.consumer_reports[0]
    assert consumer_report.submitted == 30
    assert consumer_report.dropped > 0
    assert consumer_report.processed < 30


def test_frame_dispatcher_observer_disconnect_on_error() -> None:
    sequence = MDASequence()
    sink = RecordingSink()
    observer = FailingObserver()
    dispatcher = FrameDispatcher(
        RunPolicy(noncritical_error=NonCriticalErrorPolicy.DISCONNECT)
    )
    dispatcher.add_consumer(ConsumerSpec(name="rec", consumer=sink))
    dispatcher.add_consumer(ConsumerSpec(name="observer", consumer=observer))

    dispatcher.start(sequence, {})
    dispatcher.submit(*_payload(0))
    time.sleep(0.02)
    dispatcher.submit(*_payload(1))
    dispatcher.close(sequence, RunStatus.COMPLETED)

    assert observer.calls == 1


def test_core_run_mda_v2_wiring(core: CMMCorePlus) -> None:
    sequence = MDASequence.model_validate({"time_plan": {"loops": 2, "interval": 0}})
    observer_count = 0

    class _Observer:
        def on_start(self, sequence: MDASequence, summary_meta: dict[str, Any]) -> None:
            del sequence, summary_meta

        def on_frame(
            self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
        ) -> None:
            nonlocal observer_count
            observer_count += 1
            del frame, event, meta

        def on_finish(self, sequence: MDASequence, status: RunStatus) -> None:
            del sequence, status

    thread = core.run_mda_v2(
        sequence,
        output="memory://",
        consumers=[
            ConsumerSpec(
                name="observer",
                consumer=_Observer(),
            )
        ],
    )
    thread.join()

    report = core.mda_v2.last_report
    assert report is not None
    assert report.status is RunStatus.COMPLETED
    assert report.consumer_reports
    assert report.consumer_reports[0].processed == 2
    assert observer_count == 2


def test_dispatcher_add_consumer_with_name_defined_roles() -> None:
    sequence = MDASequence()
    calls = {"start": 0, "frame": 0, "finish": 0}

    class _Consumer:
        def setup_sequence(
            self, sequence: MDASequence, summary_meta: dict[str, Any]
        ) -> None:
            calls["start"] += 1
            del sequence, summary_meta

        def on_frame(
            self, frame: np.ndarray, event: MDAEvent, meta: dict[str, Any]
        ) -> None:
            calls["frame"] += 1
            del frame, event, meta
            raise RuntimeError("observer-style frame error")

        def finish_sequence(self, sequence: MDASequence, status: RunStatus) -> None:
            calls["finish"] += 1
            del sequence, status

    dispatcher = FrameDispatcher(
        RunPolicy(
            noncritical_error=NonCriticalErrorPolicy.LOG,
            critical_error=CriticalErrorPolicy.RAISE,
        )
    )
    dispatcher.add_consumer(ConsumerSpec(name="mixed", consumer=_Consumer()))

    dispatcher.start(sequence, {})
    dispatcher.submit(*_payload(0))
    report = dispatcher.close(sequence, RunStatus.COMPLETED)

    assert calls == {"start": 1, "frame": 1, "finish": 1}
    assert report.consumer_reports == ()
