"""Signed, expiring tokens for one-click email links (e.g. clinic staff confirming an appointment)."""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

APPOINTMENT_CONFIRM_SALT = "appointment-confirm"
# Separate salt so a confirm link can never be replayed against the cancel route (or vice versa).
APPOINTMENT_CANCEL_SALT = "appointment-cancel"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_confirm_token(appointment_id):
    return _serializer().dumps(appointment_id, salt=APPOINTMENT_CONFIRM_SALT)


def verify_confirm_token(token, max_age_seconds):
    """Return the appointment id, or raise BadSignature / SignatureExpired."""
    return _serializer().loads(token, salt=APPOINTMENT_CONFIRM_SALT, max_age=max_age_seconds)


def generate_cancel_token(appointment_id):
    return _serializer().dumps(appointment_id, salt=APPOINTMENT_CANCEL_SALT)


def verify_cancel_token(token, max_age_seconds):
    """Return the appointment id, or raise BadSignature / SignatureExpired."""
    return _serializer().loads(token, salt=APPOINTMENT_CANCEL_SALT, max_age=max_age_seconds)
