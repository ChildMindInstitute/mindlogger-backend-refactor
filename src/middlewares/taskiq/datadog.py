"""Datadog tracing + distributed trace propagation for Taskiq.

Register once on the broker and every task is covered, including tasks kicked
from other tasks and scheduled tasks:

    broker.add_middlewares(DatadogTaskiqMiddleware())

Producer side (FastAPI, or a worker kicking another task):
    pre_send   -> start a `taskiq.send` span (child of the active span) and
                  inject the Datadog trace headers into message.labels
    post_send  -> finish that span

Consumer side (worker):
    pre_execute  -> extract the headers, activate the remote context, start a
                    `taskiq.execute` span that becomes the active span for the task
    post_execute -> flag the span if the task failed, then finish it
"""

from __future__ import annotations

from typing import Any

from ddtrace import tracer
from ddtrace.propagation.http import HTTPPropagator
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

LABEL_PREFIX = "dd_"


class DatadogTaskiqMiddleware(TaskiqMiddleware):
    def __init__(self, worker_service: str | None = None) -> None:
        super().__init__()
        # None -> use DD_SERVICE of the worker process.
        self._worker_service = worker_service
        self._send_spans: dict[str, Any] = {}
        self._exec_spans: dict[str, Any] = {}

    # ---- producer ---------------------------------------------------------

    def pre_send(self, message: TaskiqMessage) -> TaskiqMessage:
        # Not activated: we only want it as the parent of the remote span, and
        # we don't want to disturb the active span of the calling request.
        span = tracer.start_span(
            "taskiq.send",
            child_of=tracer.current_span(),
            resource=message.task_name,
            span_type="queue",
        )
        span.set_tag("component", "taskiq")
        span.set_tag("span.kind", "producer")
        span.set_tag("taskiq.task_id", message.task_id)
        span.set_tag("taskiq.task_name", message.task_name)

        carrier: dict[str, str] = {}
        HTTPPropagator.inject(span.context, carrier)
        for key, value in carrier.items():
            message.labels[f"{LABEL_PREFIX}{key}"] = value

        self._send_spans[message.task_id] = span
        return message

    def post_send(self, message: TaskiqMessage) -> None:
        span = self._send_spans.pop(message.task_id, None)
        if span is not None:
            span.finish()

    # ---- consumer ---------------------------------------------------------

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        carrier = {
            key[len(LABEL_PREFIX):]: value
            for key, value in message.labels.items()
            if key.startswith(LABEL_PREFIX) and isinstance(value, str)
        }
        if carrier:
            context = HTTPPropagator.extract(carrier)
            if context.trace_id:
                tracer.context_provider.activate(context)

        span = tracer.trace(
            "taskiq.execute",
            service=self._worker_service,
            resource=message.task_name,
            span_type="worker",
        )
        span.set_tag("component", "taskiq")
        span.set_tag("span.kind", "consumer")
        span.set_tag("taskiq.task_id", message.task_id)
        span.set_tag("taskiq.task_name", message.task_name)
        self._exec_spans[message.task_id] = span
        return message

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult[Any]) -> None:
        span = self._exec_spans.pop(message.task_id, None)
        if span is None:
            return
        error = result.error if result.is_err else None
        if error is not None:
            _flag_error(span, error)
        span.finish()


def _flag_error(span: Any, error: BaseException) -> None:
    if error.__traceback__ is not None:
        span.set_exc_info(type(error), error, error.__traceback__)
        return
    # Span.set_exc_info silently does nothing without a traceback, which is the
    # case for an exception that was rebuilt or returned rather than raised, so
    # flag the span ourselves.
    span.error = 1
    span.set_tag("error.type", f"{type(error).__module__}.{type(error).__qualname__}")
    span.set_tag("error.message", str(error))