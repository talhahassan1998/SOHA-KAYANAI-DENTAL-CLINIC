from datetime import datetime

from itsdangerous import BadSignature, SignatureExpired
from flask import render_template, redirect, url_for, flash, current_app, request, jsonify

from app.appointments import appointments_bp
from app.extensions import db
from app.forms import AppointmentForm, TIME_SLOTS
from app.models import Appointment, AppointmentStatus, Service, Doctor
from app.utils.availability import taken_times, is_slot_available
from app.utils.scheduling import (
    is_closed_day, is_slot_within_hours, out_of_hours_times, is_slot_in_past, past_times,
)
from app.utils.email import (
    send_appointment_confirmation, send_appointment_notification,
    send_appointment_confirmed, send_appointment_cancelled,
)
from app.utils.tokens import verify_confirm_token, verify_cancel_token


def _populate_choices(form):
    form.service.choices = [(s.id, s.name) for s in Service.query.order_by(Service.display_order).all()]
    form.doctor.choices = [(0, "Any Available Doctor")] + [
        (d.id, d.name) for d in Doctor.query.order_by(Doctor.display_order).all()
    ]


@appointments_bp.route("", methods=["GET", "POST"])
def book():
    form = AppointmentForm()
    _populate_choices(form)

    if form.validate_on_submit():
        doctor_id = form.doctor.data if form.doctor.data else None

        # Sundays are emergency care only, so they can't be booked online — enforced here
        # as well as in the UI, where Sunday dates are disabled outright.
        if is_closed_day(form.preferred_date.data):
            form.preferred_date.errors = list(form.preferred_date.errors) + [
                "We're closed for scheduled appointments on Sundays (emergency care only). "
                "Please choose another day, or call us for an emergency."
            ]
            return render_template("appointments/book.html", form=form)

        # Saturdays close early, so late slots aren't bookable that day.
        if not is_slot_within_hours(form.preferred_date.data, form.preferred_time.data):
            form.preferred_time.errors = list(form.preferred_time.errors) + [
                "We close at 4:30 PM on Saturdays. Please choose an earlier time or another day."
            ]
            return render_template("appointments/book.html", form=form)

        # A slot earlier today can't be booked. Worth re-checking on submit even though the
        # UI greys these out: the form may have sat open until the slot passed.
        if is_slot_in_past(form.preferred_date.data, form.preferred_time.data):
            form.preferred_time.errors = list(form.preferred_time.errors) + [
                "That time has already passed today. Please choose a later time or another day."
            ]
            return render_template("appointments/book.html", form=form)

        # Re-check server-side: the disabled slots in the UI can be bypassed, and another
        # patient may have taken this slot between page load and submit.
        if not is_slot_available(form.preferred_date.data, form.preferred_time.data, doctor_id):
            form.preferred_time.errors = list(form.preferred_time.errors) + [
                "Sorry, that time was just booked. Please choose another slot."
            ]
            return render_template("appointments/book.html", form=form)

        appointment = Appointment(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            service_id=form.service.data,
            doctor_id=doctor_id,
            preferred_date=form.preferred_date.data,
            preferred_time=form.preferred_time.data,
            notes=form.notes.data.strip() if form.notes.data else None,
        )
        db.session.add(appointment)
        db.session.commit()

        current_app.logger.info("New appointment booked: id=%s email=%s", appointment.id, appointment.email)

        send_appointment_confirmation(appointment)
        send_appointment_notification(appointment)

        flash("Your appointment request has been received! We'll confirm shortly by email.", "success")
        return redirect(url_for("appointments.confirmation", appointment_id=appointment.id))

    return render_template("appointments/book.html", form=form)


@appointments_bp.route("/availability")
def availability():
    """Slots that can't be booked on a date: already taken, outside that day's hours, or
    (for today) already passed."""
    try:
        preferred_date = datetime.strptime(request.args.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "date must be in YYYY-MM-DD format"}), 400

    doctor_id = request.args.get("doctor_id", type=int) or None
    all_slots = [value for value, _ in TIME_SLOTS if value]
    return jsonify({
        "taken": sorted(taken_times(preferred_date, doctor_id)),
        "closed": sorted(out_of_hours_times(preferred_date, all_slots)),
        "past": sorted(past_times(preferred_date, all_slots)),
    })


@appointments_bp.route("/confirmation/<int:appointment_id>")
def confirmation(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template("appointments/confirmation.html", appointment=appointment)


@appointments_bp.route("/confirm/<token>")
def confirm(token):
    max_age = current_app.config["APPOINTMENT_CONFIRM_TOKEN_MAX_AGE_DAYS"] * 24 * 60 * 60

    try:
        appointment_id = verify_confirm_token(token, max_age)
    except SignatureExpired:
        return render_template("appointments/confirmed.html", state="expired")
    except BadSignature:
        return render_template("appointments/confirmed.html", state="invalid")

    appointment = Appointment.query.get(appointment_id)
    if appointment is None:
        return render_template("appointments/confirmed.html", state="not_found")

    if appointment.status == AppointmentStatus.CONFIRMED:
        return render_template("appointments/confirmed.html", state="already_confirmed", appointment=appointment)

    if appointment.status == AppointmentStatus.CANCELLED:
        return render_template("appointments/confirmed.html", state="was_cancelled", appointment=appointment)

    appointment.status = AppointmentStatus.CONFIRMED
    db.session.commit()

    current_app.logger.info("Appointment confirmed: id=%s email=%s", appointment.id, appointment.email)
    send_appointment_confirmed(appointment)

    return render_template("appointments/confirmed.html", state="confirmed", appointment=appointment)


@appointments_bp.route("/cancel/<token>")
def cancel(token):
    max_age = current_app.config["APPOINTMENT_CONFIRM_TOKEN_MAX_AGE_DAYS"] * 24 * 60 * 60

    try:
        appointment_id = verify_cancel_token(token, max_age)
    except SignatureExpired:
        return render_template("appointments/confirmed.html", state="expired")
    except BadSignature:
        return render_template("appointments/confirmed.html", state="invalid")

    appointment = Appointment.query.get(appointment_id)
    if appointment is None:
        return render_template("appointments/confirmed.html", state="not_found")

    if appointment.status == AppointmentStatus.CANCELLED:
        return render_template("appointments/confirmed.html", state="already_cancelled", appointment=appointment)

    appointment.status = AppointmentStatus.CANCELLED
    db.session.commit()

    current_app.logger.info("Appointment cancelled: id=%s email=%s", appointment.id, appointment.email)
    send_appointment_cancelled(appointment)

    return render_template("appointments/confirmed.html", state="cancelled", appointment=appointment)
