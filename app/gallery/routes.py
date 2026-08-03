from flask import render_template, request

from app.gallery import gallery_bp
from app.models import GalleryImage


@gallery_bp.route("/")
def index():
    category = request.args.get("category")
    query = GalleryImage.query
    if category:
        query = query.filter_by(category=category)
    images = query.order_by(GalleryImage.display_order).all()
    categories = sorted({row[0] for row in GalleryImage.query.with_entities(GalleryImage.category).distinct()})
    return render_template("gallery/index.html", images=images, categories=categories, active_category=category)
