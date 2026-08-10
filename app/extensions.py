"""Shared Flask extension instances, initialized in the app factory."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_mail import Mail
from flask_caching import Cache
from flask_sock import Sock

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()
cache = Cache()
# Carries the voice assistant's audio relay. Needs a worker that can hold a long-lived
# connection: the dev server copes, production wants gunicorn's gevent worker.
sock = Sock()
