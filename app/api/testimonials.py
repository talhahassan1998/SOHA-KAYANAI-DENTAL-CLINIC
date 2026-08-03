from flask_restx import Namespace, Resource, fields

from app.models import Testimonial

ns = Namespace("testimonials", description="Patient testimonials")

testimonial_model = ns.model("Testimonial", {
    "id": fields.Integer,
    "patient_name": fields.String,
    "patient_photo_url": fields.String,
    "rating": fields.Integer,
    "quote": fields.String,
    "treatment": fields.String,
})


@ns.route("")
class TestimonialList(Resource):
    @ns.marshal_list_with(testimonial_model)
    def get(self):
        """List featured patient testimonials."""
        return Testimonial.query.order_by(Testimonial.display_order).all()
