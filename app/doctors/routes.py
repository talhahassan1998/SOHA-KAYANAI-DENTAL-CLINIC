from flask import render_template

from app.doctors import doctors_bp
from app.models import Doctor


@doctors_bp.route("/")
def list_doctors():
    doctors = Doctor.query.order_by(Doctor.display_order).all()
    return render_template("doctors/list.html", doctors=doctors)


@doctors_bp.route("/<slug>")
def detail(slug):
    doctor = Doctor.query.filter_by(slug=slug).first_or_404()
    others = (
        Doctor.query.filter(Doctor.id != doctor.id)
        .order_by(Doctor.display_order)
        .limit(3)
        .all()
    )
    return render_template("doctors/detail.html", doctor=doctor, others=others)
