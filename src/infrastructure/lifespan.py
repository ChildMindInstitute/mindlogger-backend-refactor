import opentelemetry.trace as trace
from fastapi import FastAPI
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from broker import broker
from config import settings


def startup_opentelemetry(app: FastAPI) -> None:
    if settings.opentelemetry.otel_exporter_otlp_traces_endpoint:
        # AWS X-ray
        if "otel" in settings.opentelemetry.otel_exporter_otlp_traces_endpoint:
            from opentelemetry.sdk.extension.aws.resource.ec2 import AwsEc2ResourceDetector
            from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
            from opentelemetry.sdk.resources import get_aggregated_resources

            span_processor = BatchSpanProcessor(OTLPSpanExporter())
            trace.set_tracer_provider(
                TracerProvider(
                    active_span_processor=span_processor,  # type: ignore [arg-type]
                    id_generator=AwsXRayIdGenerator(),
                )
            )
            trace.set_tracer_provider(TracerProvider(resource=get_aggregated_resources([AwsEc2ResourceDetector()])))
        # Local otel collector
        else:
            trace.set_tracer_provider(TracerProvider())
            trace.get_tracer_provider().add_span_processor(  # type: ignore [attr-defined]
                BatchSpanProcessor(OTLPSpanExporter()),
            )
        FastAPIInstrumentor.instrument_app(app)


async def startup_taskiq() -> None:
    if not broker.is_worker_process:
        print("Brocker startup")
        await broker.startup()


async def shutdown_taskiq() -> None:
    if not broker.is_worker_process:
        print("Brocker shutdown")
        await broker.shutdown()


def startup(app: FastAPI):
    async def _startup():
        await startup_taskiq()

    startup_opentelemetry(app)
    return _startup


def shutdown(app: FastAPI):
    async def _shutdown():
        await shutdown_taskiq()

    return _shutdown
