import pytest
import ddtrace
from ddtrace import tracer
from taskiq import InMemoryBroker, TaskiqMessage, TaskiqResult

from middlewares.taskiq.datadog import LABEL_PREFIX, DatadogTaskiqMiddleware


@pytest.fixture
def finished_spans(monkeypatch):
    """Collect every span as it finishes, without needing a Datadog agent."""
    spans = []

    probe = tracer.start_span("probe")
    span_cls = type(probe)  # ddtrace.Span / ddtrace.trace.Span depending on version
    probe.finish()

    original_finish = span_cls.finish

    def recording_finish(self, *args, **kwargs):
        spans.append(self)
        return original_finish(self, *args, **kwargs)

    monkeypatch.setattr(span_cls, "finish", recording_finish)

    tracer.context_provider.activate(None)
    yield spans
    tracer.context_provider.activate(None)


def by_name(spans, name):
    found = [s for s in spans if s.name == name]
    assert len(found) == 1, f"expected one {name!r} span, got {[s.name for s in spans]}"
    return found[0]


def make_message(labels=None) -> TaskiqMessage:
    return TaskiqMessage(
        task_id="task-1",
        task_name="tests:my_task",
        labels=labels or {},
        args=[],
        kwargs={},
    )


def ok_result() -> TaskiqResult:
    return TaskiqResult(is_err=False, log=None, return_value=1, execution_time=0.0)


def err_result(exc: BaseException) -> TaskiqResult:
    return TaskiqResult(
        is_err=True, log=None, return_value=None, execution_time=0.0, error=exc
    )


def test_send_injects_labels_and_parents_to_active_span(finished_spans):
    mw = DatadogTaskiqMiddleware()
    msg = make_message()

    with tracer.trace("http.request") as request_span:
        mw.pre_send(msg)
        assert not finished_spans  # send span stays open until post_send
        mw.post_send(msg)

    send = by_name(finished_spans, "taskiq.send")
    assert send.parent_id == request_span.span_id
    assert send.trace_id == request_span.trace_id
    assert send.resource == "tests:my_task"
    assert send.get_tag("taskiq.task_id") == "task-1"

    # the remote parent must be the send span, not the request span
    assert msg.labels[f"{LABEL_PREFIX}x-datadog-parent-id"] == str(send.span_id)
    assert f"{LABEL_PREFIX}x-datadog-trace-id" in msg.labels


def test_execute_continues_trace_from_labels(finished_spans):
    mw = DatadogTaskiqMiddleware()
    msg = make_message()

    with tracer.trace("http.request"):
        mw.pre_send(msg)
        mw.post_send(msg)
    send = by_name(finished_spans, "taskiq.send")

    # Simulate the worker: fresh context, only the labels survive.
    tracer.context_provider.activate(None)
    worker_msg = make_message(dict(msg.labels))

    mw.pre_execute(worker_msg)
    assert tracer.current_span().name == "taskiq.execute"  # task code runs under it
    mw.post_execute(worker_msg, ok_result())

    execute = by_name(finished_spans, "taskiq.execute")
    assert execute.trace_id == send.trace_id
    assert execute.parent_id == send.span_id
    assert execute.error == 0


def test_failed_task_flags_span_as_error(finished_spans):
    mw = DatadogTaskiqMiddleware()
    msg = make_message()

    # Raised for real, so the exception carries a traceback like it does in a worker.
    try:
        raise ValueError("boom")
    except ValueError as exc:
        error = exc

    mw.pre_execute(msg)
    mw.post_execute(msg, err_result(error))

    execute = by_name(finished_spans, "taskiq.execute")
    assert execute.error == 1
    assert execute.get_tag("error.message") == "boom"
    assert execute.get_tag("error.type") == "builtins.ValueError"
    assert execute.get_tag("error.stack")


def test_failed_task_without_traceback_still_flags_span(finished_spans):
    mw = DatadogTaskiqMiddleware()
    msg = make_message()

    mw.pre_execute(msg)
    mw.post_execute(msg, err_result(ValueError("boom")))  # never raised: no traceback

    execute = by_name(finished_spans, "taskiq.execute")
    assert execute.error == 1
    assert execute.get_tag("error.message") == "boom"
    assert execute.get_tag("error.type") == "builtins.ValueError"


def test_execute_without_labels_starts_a_new_trace(finished_spans):
    mw = DatadogTaskiqMiddleware()
    msg = make_message()  # e.g. scheduled task, or sent by a non-instrumented producer

    mw.pre_execute(msg)
    mw.post_execute(msg, ok_result())

    execute = by_name(finished_spans, "taskiq.execute")
    assert not execute.parent_id


@pytest.mark.asyncio
async def test_end_to_end_with_in_memory_broker(finished_spans):
    broker = InMemoryBroker(await_inplace=True).with_middlewares(
        DatadogTaskiqMiddleware()
    )

    @broker.task
    async def add(a: int, b: int) -> int:
        return a + b

    await broker.startup()
    try:
        with tracer.trace("http.request") as request_span:
            task = await add.kiq(1, 2)
            result = await task.wait_result(timeout=5)
        assert result.return_value == 3
    finally:
        await broker.shutdown()

    send = by_name(finished_spans, "taskiq.send")
    execute = by_name(finished_spans, "taskiq.execute")
    assert send.parent_id == request_span.span_id
    assert execute.parent_id == send.span_id
    assert execute.trace_id == request_span.trace_id


def test_override_service_name():
    mw = DatadogTaskiqMiddleware(worker_service="test-service")
    assert mw._worker_service == "test-service"


def test_default_service_name(monkeypatch):
    ddtrace.config.service = "test-service"
    mw = DatadogTaskiqMiddleware()
    assert mw._worker_service == "test-service"