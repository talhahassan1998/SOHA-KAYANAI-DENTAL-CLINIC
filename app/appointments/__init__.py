from flask import Blueprint

appointments_bp = Blueprint("appointments", __name__, url_prefix="/book-appointment")

from app.appointments import routes  # noqa: E402,F401
