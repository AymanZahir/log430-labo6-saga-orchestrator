"""
Saga Orchestrator
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
from flask import Flask, jsonify, request
from controllers.order_saga_controller import OrderSagaController
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

app = Flask(__name__)

# Configure OpenTelemetry and Jaeger exporter
resource = Resource.create({
    "service.name": "saga-orchestrator",
    "service.version": "1.0.0"
})
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(
    endpoint="http://jaeger:4317",
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
tracer = trace.get_tracer(__name__)

@app.get('/health-check')
def health():
    """ Return OK if app is up and running """
    with tracer.start_as_current_span("health-check"):
        return jsonify({'status': 'ok'})

@app.post('/saga/order')
def saga_order():
    """ Start order saga """
    with tracer.start_as_current_span("saga-order"):
        order_saga_controller = OrderSagaController()
        result = order_saga_controller.run(request)

        if result["status"] == "OK":
            return jsonify(result), 200
        else:
            return jsonify(result), 500

# Start Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.FLASK_PORT)
