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

    # Voice assistant. Two providers are supported; whichever key is configured wins, with
    # Gemini preferred when both are (it has a free tier). In either case the standing key
    # never leaves the server — it only mints the short-lived token the browser connects
    # with. With no key at all the widget isn't rendered, so the site runs unchanged.
    #
    # Gemini talks over a WebSocket carrying raw PCM; OpenAI uses WebRTC. See
    # app/utils/gemini_client.py and app/utils/openai_client.py.
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    # The id published in Google's docs isn't visible to every key — this alias is, and it
    # survives preview snapshots being retired. Check with GET /v1beta/models before changing.
    # Measured against gemini-2.5-flash-native-audio-latest on the same prompt and tools:
    # first audio 1.55s vs 12.53s, audio on 3/3 runs vs 2/3, transcripts on 3/3 vs 2/3, and
    # check_availability + fill_booking_form called on every run rather than intermittently.
    # It's a preview model, so pin the 2.5 id here if it ever regresses.
    GEMINI_LIVE_MODEL = os.environ.get("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
    GEMINI_LIVE_VOICE = os.environ.get("GEMINI_LIVE_VOICE", "Kore")
    # Text model behind the transcript's English translations. Deliberately a small one: the
    # job is one short line at a time, and it never touches the conversation itself.
    GEMINI_TRANSLATE_MODEL = os.environ.get("GEMINI_TRANSLATE_MODEL", "gemini-flash-lite-latest")
    # Off by default: it sends transcript lines to Google a second time, which is the kind of
    # thing a clinic should switch on deliberately rather than inherit.
    VOICE_TRANSLATE_ENABLED = _bool(os.environ.get("VOICE_TRANSLATE_ENABLED"), False)
    # One call per spoken turn, so this tracks conversation length rather than page views.
    VOICE_TRANSLATE_RATE_LIMIT = int(os.environ.get("VOICE_TRANSLATE_RATE_LIMIT", 120))

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_REALTIME_MODEL = os.environ.get("OPENAI_REALTIME_MODEL", "gpt-realtime-2.1")
    OPENAI_REALTIME_VOICE = os.environ.get("OPENAI_REALTIME_VOICE", "marin")
    VOICE_ASSISTANT_ENABLED = _bool(os.environ.get("VOICE_ASSISTANT_ENABLED"), True)
    # Each token starts a billable call, so cap how many one visitor can open.
    VOICE_TOKEN_RATE_LIMIT = int(os.environ.get("VOICE_TOKEN_RATE_LIMIT", 10))
    VOICE_TOKEN_RATE_WINDOW = int(os.environ.get("VOICE_TOKEN_RATE_WINDOW", 3600))
    # Relay reconnects get a wider budget on their own counter: one conversation reopens the
    # socket every time the assistant moves the patient to another page, so a per-session
    # limit would cut off anyone who browsed while talking.
    VOICE_STREAM_RATE_LIMIT = int(os.environ.get("VOICE_STREAM_RATE_LIMIT", 60))
    # Reconnects after a page load are the same conversation continuing, so they get their
    # own much wider budget: a single booking navigates three or four times, and counting
    # those against the new-conversation limit locked people out mid-booking.
    VOICE_STREAM_RESUME_LIMIT = int(os.environ.get("VOICE_STREAM_RESUME_LIMIT", 400))

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True

    database_url = os.environ.get("DATABASE_URL")

    if database_url and database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql+psycopg://", 1
        )

    SQLALCHEMY_DATABASE_URI = database_url or f"sqlite:///{BASE_DIR / 'instance' / 'dental_clinic.db'}"

    @staticmethod
    def init_app(app):
        @app.after_request
        def no_cache_while_developing(response):
            """Stop the browser reusing yesterday's page.

            The voice widget's JavaScript is inlined in the HTML rather than served as a
            static file, so a cached page means cached behaviour: edits appear to have no
            effect, and a half-updated tab can talk to a fully-updated server. That cost
            real time to track down once — the browser was still running a build from
            before a fix while the server had already reloaded.
            """
            if response.status_code < 400:
                response.headers["Cache-Control"] = "no-store, must-revalidate"
            return response


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
