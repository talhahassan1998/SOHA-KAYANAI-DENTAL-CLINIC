from flask_restx import Namespace, Resource, fields

from app.models import Service

ns = Namespace("services", description="Dental services offered")

service_model = ns.model("Service", {
    "id": fields.Integer,
    "name": fields.String,
    "slug": fields.String,
    "short_description": fields.String,
    "full_description": fields.String,
    "icon_name": fields.String,
    "image_url": fields.String,
})


@ns.route("")
class ServiceList(Resource):
    @ns.marshal_list_with(service_model)
    def get(self):
        """List all services, ordered for display."""
        return Service.query.order_by(Service.display_order).all()


@ns.route("/<int:service_id>")
@ns.response(404, "Service not found")
class ServiceDetail(Resource):
    @ns.marshal_with(service_model)
    def get(self, service_id):
        """Fetch a single service by id."""
        return Service.query.get_or_404(service_id)
