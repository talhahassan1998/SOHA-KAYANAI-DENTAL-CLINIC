from datetime import date, datetime

from flask_restx import Namespace, Resource, fields
from email_validator import validate_email, EmailNotValidError

from app.extensions import db
from app.models import Appointment, Service, Doctor
from app.utils.email import send_appointment_confirmation, send_appointment_notification
from app.utils.scheduling import is_slot_in_past

ns = Namespace("appointments", description="Book an appointment via the API")

appointment_input = ns.model("AppointmentInput", {
    "full_name": fields.String(required=True, max_length=160),
    "email": fields.String(required=True),
    "phone": fields.String(required=True, max_length=40),
    "service_id": fields.Integer(required=True),
    "doctor_id": fields.Integer(required=False, description="Omit for any available doctor"),
    "preferred_date": fields.String(required=True, description="YYYY-MM-DD"),
    "preferred_time": fields.String(required=True),
    "notes": fields.String(required=False),
})

appointment_output = ns.model("AppointmentOutput", {
    "id": fields.Integer,
    "full_name": fields.String,
    "email": fields.String,
    "phone": fields.String,
    "service_id": fields.Integer,
    "doctor_id": fields.Integer,
    "preferred_date": fields.String,
    "preferred_time": fields.String,
    "notes": fields.String,
    "status": fields.String,
})


@ns.route("")
class AppointmentCreate(Resource):
    @ns.expect(appointment_input, validate=True)
    @ns.marshal_with(appointment_output, code=201)
    def post(self):
        """Submit a new appointment request."""
        data = ns.payload

        try:
            validate_email(data["email"], check_deliverability=False)
        except EmailNotValidError:
            ns.abort(400, "Invalid email address")

        service = Service.query.get(data["service_id"])
        if not service:
            ns.abort(400, "Invalid service_id")

        doctor_id = data.get("doctor_id")
        if doctor_id and not Doctor.query.get(doctor_id):
            ns.abort(400, "Invalid doctor_id")

        try:
            preferred_date = datetime.strptime(data["preferred_date"], "%Y-%m-%d").date()
        except ValueError:
            ns.abort(400, "preferred_date must be in YYYY-MM-DD format")

        if preferred_date < date.today():
            ns.abort(400, "preferred_date cannot be in the past")

        if is_slot_in_past(preferred_date, data["preferred_time"]):
            ns.abort(400, "preferred_time has already passed today")

        appointment = Appointment(
            full_name=data["full_name"].strip(),
            email=data["email"].strip().lower(),
            phone=data["phone"].strip(),
            service_id=service.id,
            doctor_id=doctor_id or None,
            preferred_date=preferred_date,
            preferred_time=data["preferred_time"],
            notes=data.get("notes"),
        )
        db.session.add(appointment)
        db.session.commit()

        send_appointment_confirmation(appointment)
        send_appointment_notification(appointment)

        return appointment, 201
