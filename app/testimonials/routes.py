from flask import render_template

from app.testimonials import testimonials_bp
from app.models import Testimonial


@testimonials_bp.route("/")
def index():
    testimonials = Testimonial.query.order_by(Testimonial.display_order).all()
    return render_template("testimonials/index.html", testimonials=testimonials)
