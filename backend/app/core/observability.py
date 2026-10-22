from app.core.config import get_settings


def setup_otel(app) -> None:
    ep = get_settings().otlp_endpoint
    if not ep:
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "cloudpulse-api"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=ep)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
