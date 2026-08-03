from flask import Blueprint

blog_bp = Blueprint("blog", __name__, url_prefix="/blog")

from app.blog import routes  # noqa: E402,F401
