"""Shared Flask extension instances, initialized in the app factory."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_mail import Mail
from flask_caching import Cache

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()
cache = Cache()
