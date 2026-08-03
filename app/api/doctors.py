from flask_restx import Namespace, Resource, fields

from app.models import Doctor

ns = Namespace("doctors", description="Doctor directory")

doctor_model = ns.model("Doctor", {
    "id": fields.Integer,
    "name": fields.String,
    "slug": fields.String,
    "specialty": fields.String,
    "credentials": fields.String,
    "bio": fields.String,
    "photo_url": fields.String,
    "years_experience": fields.Integer,
})


@ns.route("")
class DoctorList(Resource):
    @ns.marshal_list_with(doctor_model)
    def get(self):
        """List all doctors, ordered for display."""
        return Doctor.query.order_by(Doctor.display_order).all()


@ns.route("/<int:doctor_id>")
@ns.response(404, "Doctor not found")
class DoctorDetail(Resource):
    @ns.marshal_with(doctor_model)
    def get(self, doctor_id):
        """Fetch a single doctor by id."""
        return Doctor.query.get_or_404(doctor_id)
