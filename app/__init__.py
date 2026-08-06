"""Application factory for the dental clinic Flask app."""
import logging

from flask import Flask, render_template

from config import config
from app.extensions import db, migrate, csrf, mail, cache


def create_app(config_name="default"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)
    register_context_processors(app)

    if not app.debug and not app.testing:
        app.logger.setLevel(logging.INFO)

    return app


def register_blueprints(app):
    from app.main import main_bp
    from app.appointments import appointments_bp
    from app.services import services_bp
    from app.doctors import doctors_bp
    from app.blog import blog_bp
    from app.gallery import gallery_bp
    from app.testimonials import testimonials_bp
    from app.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(doctors_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(testimonials_bp)
    app.register_blueprint(api_bp)

    # The REST API is a stateless JSON API with no session/cookie flow, so it is
    # exempt from the session-based CSRF protection applied to HTML form POSTs.
    from app.extensions import csrf
    csrf.exempt(api_bp)


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Server error: %s", error)
        return render_template("errors/500.html"), 500


def register_context_processors(app):
    @app.context_processor
    def inject_clinic_info():
        from datetime import datetime
        return {
            "current_year": datetime.utcnow().year,
            "clinic_name": app.config["CLINIC_NAME"],
            "clinic_phone": app.config["CLINIC_PHONE"],
            "clinic_address": app.config["CLINIC_ADDRESS"],
            "clinic_whatsapp_number": app.config["CLINIC_WHATSAPP_NUMBER"],
            "google_maps_query": app.config["GOOGLE_MAPS_QUERY"],
            "facebook_url": app.config["FACEBOOK_URL"],
            "instagram_url": app.config["INSTAGRAM_URL"],
            "twitter_url": app.config["TWITTER_URL"],
            "linkedin_url": app.config["LINKEDIN_URL"],
        }

    @app.context_processor
    def inject_gender_label():
        # Appointments predating the gender field have no value, so templates need a helper
        # that renders those as "Not specified" rather than a blank cell.
        from app.models import Gender
        return {"gender_label": Gender.label}

    @app.context_processor
    def inject_newsletter_form():
        from app.forms import NewsletterForm
        return {"newsletter_form": NewsletterForm()}


def register_cli(app):
    @app.cli.command("seed")
    def seed():
        """Populate the database with sample data."""
        from seed import run_seed
        run_seed()
        print("Database seeded successfully.")
