"""Application configuration objects, selected at runtime via FLASK_ENV."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-not-secure-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    APPOINTMENT_CONFIRM_TOKEN_MAX_AGE_DAYS = int(
        os.environ.get("APPOINTMENT_CONFIRM_TOKEN_MAX_AGE_DAYS", 30)
    )

    # The clinic's wall-clock timezone. "Today's" already-passed time slots are worked out
    # against this, not the server's local clock, so booking stays correct when the app runs
    # in a UTC container (as the Docker image does).
    CLINIC_TIMEZONE = os.environ.get("CLINIC_TIMEZONE", "Asia/Karachi")

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = _bool(os.environ.get("MAIL_USE_TLS"), True)
    MAIL_USE_SSL = _bool(os.environ.get("MAIL_USE_SSL"), False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@sohakayanidental.pk")
    MAIL_SUPPRESS_SEND = _bool(os.environ.get("MAIL_SUPPRESS_SEND"), True)

    CLINIC_NOTIFY_EMAIL = os.environ.get("CLINIC_NOTIFY_EMAIL", "front-desk@sohakayanidental.pk")
    CLINIC_NAME = os.environ.get("CLINIC_NAME", "Soha Kayani Dental Clinic")
    CLINIC_PHONE = os.environ.get("CLINIC_PHONE", "+92 51 111 555 000")
    CLINIC_ADDRESS = os.environ.get(
        "CLINIC_ADDRESS",
        "F3 Centre of Informatics, Commercial Area, Sector B - Zaraj Housing Scheme, Opposite Giga Mall, Islamabad",
    )
    CLINIC_WHATSAPP_NUMBER = os.environ.get("CLINIC_WHATSAPP_NUMBER", "923001234567")
    GOOGLE_MAPS_QUERY = os.environ.get(
        "GOOGLE_MAPS_QUERY", "F3 Centre of Informatics, Zaraj Housing Scheme, Islamabad, Pakistan"
    )

    FACEBOOK_URL = os.environ.get("FACEBOOK_URL", "https://facebook.com")
    INSTAGRAM_URL = os.environ.get("INSTAGRAM_URL", "https://instagram.com")
    TWITTER_URL = os.environ.get("TWITTER_URL", "https://twitter.com")
    LINKEDIN_URL = os.environ.get("LINKEDIN_URL", "https://linkedin.com")

    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    RESTX_MASK_SWAGGER = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or f"sqlite:///{BASE_DIR / 'instance' / 'dental_clinic.db'}"


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    DEBUG = False
    _db_url = os.environ.get("DATABASE_URL", "")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif _db_url.startswith("postgresql://"):
        _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{BASE_DIR / 'instance' / 'dental_clinic.db'}"

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        import logging
        from logging.handlers import RotatingFileHandler

        # Serverless hosts (Vercel/Lambda) have a read-only filesystem — log to stdout there.
        if os.environ.get("VERCEL"):
            handler = logging.StreamHandler()
        else:
            log_dir = BASE_DIR / "logs"
            log_dir.mkdir(exist_ok=True)
            handler = RotatingFileHandler(log_dir / "dental_clinic.log", maxBytes=1_000_000, backupCount=5)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        ))
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
