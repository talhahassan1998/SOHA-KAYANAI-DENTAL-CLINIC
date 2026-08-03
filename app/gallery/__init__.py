from flask import Blueprint

gallery_bp = Blueprint("gallery", __name__, url_prefix="/gallery")

from app.gallery import routes  # noqa: E402,F401
