from flask import Blueprint

doctors_bp = Blueprint("doctors", __name__, url_prefix="/doctors")

from app.doctors import routes  # noqa: E402,F401
