"""Flask-RESTX API blueprint, mounted at /api/v1 with Swagger docs at /api/v1/docs."""
from flask import Blueprint
from flask_restx import Api

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

api = Api(
    api_bp,
    version="1.0",
    title="Dental Clinic API",
    description="Public REST API for the dental clinic website (doctors, services, testimonials, appointments).",
    doc="/docs",
)

from app.api.doctors import ns as doctors_ns  # noqa: E402
from app.api.services import ns as services_ns  # noqa: E402
from app.api.testimonials import ns as testimonials_ns  # noqa: E402
from app.api.appointments import ns as appointments_ns  # noqa: E402

api.add_namespace(doctors_ns, path="/doctors")
api.add_namespace(services_ns, path="/services")
api.add_namespace(testimonials_ns, path="/testimonials")
api.add_namespace(appointments_ns, path="/appointments")
