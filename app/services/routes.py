from flask import render_template, abort

from app.services import services_bp
from app.models import Service


@services_bp.route("/")
def list_services():
    services = Service.query.order_by(Service.display_order).all()
    return render_template("services/list.html", services=services)


@services_bp.route("/<slug>")
def detail(slug):
    service = Service.query.filter_by(slug=slug).first_or_404()
    related = (
        Service.query.filter(Service.id != service.id)
        .order_by(Service.display_order)
        .limit(3)
        .all()
    )
    return render_template("services/detail.html", service=service, related=related)
