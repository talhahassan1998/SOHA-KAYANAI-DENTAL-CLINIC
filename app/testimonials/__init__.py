from flask import Blueprint

testimonials_bp = Blueprint("testimonials", __name__, url_prefix="/testimonials")

from app.testimonials import routes  # noqa: E402,F401
