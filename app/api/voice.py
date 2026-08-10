"""Voice assistant endpoints: realtime session tokens plus the tools the assistant calls.

Everything arriving here originated as speech interpreted by a language model, so it is
treated as untrusted input and validated exactly as strictly as a form post would be. In
particular /book runs the same guard chain as the HTML booking route, so a spoken booking
can't take a Sunday, a Saturday evening, a slot that has already passed, or a chair that
somebody else just claimed.

Mounted under api_bp, which is CSRF-exempt (see register_blueprints in app/__init__.py),
so the page can call these with plain fetch.
"""
from datetime import datetime
from difflib import SequenceMatcher

from email_validator import validate_email, EmailNotValidError
from flask import current_app, url_for
from flask_restx import Namespace, Resource, fields

from app.extensions import db
from app.forms import TIME_SLOTS
from app.models import Appointment, ContactMessage, Doctor, FAQ, Gender, Service
from app.utils.availability import is_slot_available, taken_times
from app.utils.email import (
    send_appointment_confirmation, send_appointment_notification,
    send_contact_autoreply, send_contact_notification,
)
from app.utils.gemini_client import mint_ephemeral_token, translate_to_english
from app.utils.openai_client import VoiceAssistantError, mint_client_secret
from app.utils.rate_limit import contact_rate_limited, rate_limited
from app.utils.voice_provider import GEMINI, active_provider
from app.utils.scheduling import (
    clinic_now, is_closed_day, is_slot_in_past, is_slot_within_hours, out_of_hours_times,
    past_times,
)

ns = Namespace("voice", description="Realtime voice assistant session and tools")

ALL_SLOTS = [value for value, _ in TIME_SLOTS if value]

# Documented for Swagger, but deliberately NOT enforced with @ns.expect(validate=True):
# RESTX's rejection is a 400 with its own error shape, which reaches the assistant as a
# broken tool rather than as something it can explain and correct. Every field is checked
# by hand below instead, so a mishearing comes back as a sentence it can read out.
book_input = ns.model("VoiceBookingInput", {
    "full_name": fields.String(required=True),
    "email": fields.String(required=True),
    "phone": fields.String(required=True),
    "gender": fields.String(required=True, enum=Gender.CHOICES),
    "service_name": fields.String(required=True),
    "doctor_name": fields.String(required=False),
    "date": fields.String(required=True, description="YYYY-MM-DD"),
    "time": fields.String(required=True),
    "notes": fields.String(required=False),
})

contact_input = ns.model("VoiceContactInput", {
    "name": fields.String(required=True),
    "email": fields.String(required=True),
    "phone": fields.String(required=False),
    "subject": fields.String(required=False),
    "message": fields.String(required=True),
})


def _fail(message):
    """A refusal the assistant can read out loud.

    Deliberately HTTP 200 with ok=false: a 4xx would surface to the model as a broken tool
    rather than as a reason it can explain to the patient.
    """
    return {"ok": False, "message": message}


def _ok(message, **extra):
    return {"ok": True, "message": message, **extra}


def _match_by_name(rows, name):
    """Resolve a spoken name to a row: exact first, then substring, then None.

    Returns (row, ambiguous). Speech gives approximations — "whitening" for "Teeth
    Whitening" — so an exact match can't be required, but a query matching several rows
    must not silently pick the first.
    """
    if not name:
        return None, False

    needle = name.strip().lower()
    if not needle:
        return None, False

    for row in rows:
        if row.name.lower() == needle:
            return row, False

    partial = [row for row in rows if needle in row.name.lower() or row.name.lower() in needle]
    if len(partial) == 1:
        return partial[0], False
    if len(partial) > 1:
        return None, True

    # Nothing matched as a substring. Urdu and Arabic names reach us through speech-to-text
    # with the spelling it happened to pick — Ahmad/Ahmed, Ayesha/Aisha, Mahnoor/Mehnoor —
    # and those share no substring with the stored name, so the patient was told the dentist
    # doesn't work here. Compare word by word allowing a small difference, which catches the
    # transliterations without letting two genuinely different names collide.
    fuzzy = [row for row in rows if _names_are_close(needle, row.name.lower())]
    if len(fuzzy) == 1:
        return fuzzy[0], False
    if len(fuzzy) > 1:
        return None, True
    return None, False


# Honorifics carry no identifying information and the patient may or may not say them.
_NAME_NOISE = {"dr", "dr.", "doctor", "mr", "mrs", "ms", "miss"}


def _significant_words(text):
    return [w.strip(".,") for w in text.split() if w.strip(".,") not in _NAME_NOISE and w.strip(".,")]


def _names_are_close(spoken, stored):
    """True when every word the patient said closely matches a word in the stored name.

    Requires all spoken words to land, so "Ayesha" matches "Dr. Ayesha Farooq" but "Ayesha
    Siddiqui" does not match a different Ayesha.
    """
    spoken_words = _significant_words(spoken)
    stored_words = _significant_words(stored)
    if not spoken_words or not stored_words:
        return False
    return all(any(_word_is_close(s, t) for t in stored_words) for s in spoken_words)


# Transliterated variants of the same name (Aisha/Ayesha, Ahmad/Ahmed, Mehnoor/Mahnoor)
# score from about 0.73 up. Unrelated names score far lower — but a few genuinely different
# names sit in the same band (Bilal/Hilal both score 0.80), so this threshold cannot be
# trusted on its own. _match_by_name treats two or more fuzzy candidates as ambiguous and
# makes the assistant ask, which is the right outcome for a booking either way.
_NAME_SIMILARITY = 0.72


def _word_is_close(a, b):
    """One spelling of a name against another, tolerating a vowel's worth of difference."""
    if a == b:
        return True
    # Only compare words of similar length: "ali" and "alishba" are different people.
    if abs(len(a) - len(b)) > 2 or min(len(a), len(b)) < 4:
        return False
    return SequenceMatcher(None, a, b).ratio() >= _NAME_SIMILARITY


def _parse_date(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


# Slot values are zero-padded ("03:00 PM") but the labels everyone reads and says are not
# ("3:00 PM"), and a voice model transcribes what it hears. Insisting on the padded form
# rejected most of the day — every hour before ten and every afternoon slot — so accept the
# ways a time actually arrives and normalise to the stored value. 24-hour input is included
# because Urdu and Arabic speakers routinely give the time that way.
_TIME_INPUT_FORMATS = ("%I:%M %p", "%I %p", "%H:%M")


def _parse_time(value):
    """Normalise a spoken time to a slot value, or None if it isn't one of ours."""
    raw = " ".join((value or "").strip().upper().split())
    if not raw:
        return None

    for fmt in _TIME_INPUT_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        slot = parsed.strftime("%I:%M %p")
        if slot in ALL_SLOTS:
            return slot
        return None
    return None


@ns.route("/token")
class VoiceToken(Resource):
    def post(self):
        """Mint a short-lived credential for a realtime voice session.

        The response carries the provider so the page knows which transport to open; the
        two backends' credentials are not interchangeable.
        """
        cfg = current_app.config
        provider = active_provider(cfg)
        if provider is None:
            ns.abort(503, "The voice assistant is not enabled.")

        if rate_limited("voice-token", cfg["VOICE_TOKEN_RATE_LIMIT"], cfg["VOICE_TOKEN_RATE_WINDOW"]):
            ns.abort(429, "Too many voice sessions from this connection. Please try again later.")

        try:
            if provider == GEMINI:
                # No credential goes to the browser: Gemini's ephemeral tokens are minted
                # fine but rejected at connect time (Preview limitation), so the page opens
                # a relay on this server instead and the key never leaves it.
                return {
                    "provider": "gemini",
                    "stream_path": "/api/v1/voice/stream",
                    "model": cfg["GEMINI_LIVE_MODEL"],
                }
            return mint_client_secret()
        except VoiceAssistantError as exc:
            current_app.logger.warning("Voice token request failed: %s", exc)
            ns.abort(502, "Could not start the voice assistant. Please try again.")


@ns.route("/translate")
class VoiceTranslate(Resource):
    def post(self):
        """English rendering of one transcript line, for the on-screen log.

        Display only. The result never re-enters the conversation and is never used to book
        anything — the patient keeps talking to the assistant in their own language, and a
        wrong translation can only mislead someone reading the panel.
        """
        cfg = current_app.config
        if not cfg["VOICE_TRANSLATE_ENABLED"]:
            return _fail("Translation is not enabled.")

        data = ns.payload or {}
        text = (data.get("text") or "").strip()
        if not text:
            return _fail("There is nothing to translate.")

        # Its own budget rather than the session counter: this fires once per spoken turn, so
        # a long conversation would otherwise eat the allowance for starting new ones.
        if rate_limited("voice-translate", cfg["VOICE_TRANSLATE_RATE_LIMIT"],
                        cfg["VOICE_TOKEN_RATE_WINDOW"]):
            return _fail("Too many translations from this connection.")

        try:
            translated = translate_to_english(text)
        except VoiceAssistantError as exc:
            current_app.logger.warning("Transcript translation failed: %s", exc)
            return _fail("That line couldn't be translated.")

        if translated is None:
            return _fail("That line couldn't be translated.")
        return _ok("Translated.", text=translated)


@ns.route("/info")
class VoiceInfo(Resource):
    def post(self):
        """Read-only clinic facts for the assistant to answer questions from."""
        data = ns.payload or {}
        topic = (data.get("topic") or "").strip().lower()
        query = (data.get("query") or "").strip().lower()

        if topic == "services":
            rows = Service.query.order_by(Service.display_order).all()
            if query:
                rows = [r for r in rows if query in r.name.lower()
                        or query in (r.short_description or "").lower()] or rows
            return _ok("Services retrieved.", services=[
                {"name": r.name, "description": r.short_description} for r in rows[:20]
            ])

        if topic == "doctors":
            rows = Doctor.query.order_by(Doctor.display_order).all()
            if query:
                rows = [r for r in rows if query in r.name.lower()
                        or query in r.specialty.lower()] or rows
            return _ok("Doctors retrieved.", doctors=[
                {
                    "name": r.name,
                    "specialty": r.specialty,
                    "credentials": r.credentials,
                    "years_experience": r.years_experience,
                }
                for r in rows[:20]
            ])

        if topic == "faqs":
            rows = FAQ.query.order_by(FAQ.display_order).all()
            if query:
                rows = [r for r in rows if query in r.question.lower()
                        or query in r.answer.lower()] or rows
            return _ok("FAQs retrieved.", faqs=[
                {"question": r.question, "answer": r.answer} for r in rows[:10]
            ])

        if topic == "hours":
            return _ok("Opening hours retrieved.", hours={
                "monday_to_friday": "9:00 AM - 7:00 PM (closed 1:00 - 2:00 PM)",
                "saturday": "9:00 AM - 4:30 PM",
                "sunday": "Closed for scheduled appointments - emergency care only",
                "timezone": "Pakistan Standard Time",
            })

        if topic == "contact":
            cfg = current_app.config
            return _ok("Contact details retrieved.", contact={
                "clinic_name": cfg["CLINIC_NAME"],
                "phone": cfg["CLINIC_PHONE"],
                "address": cfg["CLINIC_ADDRESS"],
            })

        return _fail("I don't have that kind of information available.")


@ns.route("/availability")
class VoiceAvailability(Resource):
    def post(self):
        """Which slots are genuinely free on a date."""
        data = ns.payload or {}

        preferred_date = _parse_date(data.get("date"))
        if preferred_date is None:
            return _fail("I couldn't understand that date. Please say it again.")

        if preferred_date < clinic_now().date():
            return _fail("That date has already passed. Please offer a date in the future.")

        if is_closed_day(preferred_date):
            return _fail(
                "The clinic is closed for scheduled appointments on Sundays — emergency care only. "
                "Please suggest another day."
            )

        doctor = None
        if data.get("doctor_name"):
            doctor, ambiguous = _match_by_name(Doctor.query.all(), data["doctor_name"])
            if ambiguous:
                return _fail("Several dentists match that name. Please ask which one they mean.")
            if doctor is None:
                return _fail("No dentist by that name works here. Offer to check any available dentist.")

        unavailable = (
            taken_times(preferred_date, doctor.id if doctor else None)
            | out_of_hours_times(preferred_date, ALL_SLOTS)
            | past_times(preferred_date, ALL_SLOTS)
        )
        available = [slot for slot in ALL_SLOTS if slot not in unavailable]

        if not available:
            return _ok(
                "No times are left on that date. Suggest another day.",
                date=preferred_date.isoformat(), available_times=[],
            )

        return _ok(
            "Available times retrieved.",
            date=preferred_date.isoformat(),
            doctor=doctor.name if doctor else "Any available dentist",
            available_times=available,
        )


@ns.route("/book")
class VoiceBook(Resource):
    @ns.expect(book_input)
    def post(self):
        """Create a real appointment from a voice conversation."""
        data = ns.payload or {}

        full_name = (data.get("full_name") or "").strip()
        if len(full_name) < 2:
            return _fail("I need the patient's full name.")

        email = (data.get("email") or "").strip().lower()
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            return _fail("That email address doesn't look right. Please confirm it.")

        phone = (data.get("phone") or "").strip()
        if not 7 <= len(phone) <= 20:
            return _fail("That phone number doesn't look right. Please confirm it.")

        if data.get("gender") not in Gender.CHOICES:
            return _fail("Please ask the patient how they'd like their gender recorded.")

        service, ambiguous = _match_by_name(Service.query.all(), data.get("service_name"))
        if ambiguous:
            return _fail("Several treatments match that. Please ask which one they mean.")
        if service is None:
            return _fail("We don't offer a treatment by that name. Offer to list the treatments.")

        doctor = None
        if data.get("doctor_name"):
            doctor, ambiguous = _match_by_name(Doctor.query.all(), data["doctor_name"])
            if ambiguous:
                return _fail("Several dentists match that name. Please ask which one they mean.")
            if doctor is None:
                return _fail("No dentist by that name works here. Offer any available dentist.")

        preferred_date = _parse_date(data.get("date"))
        if preferred_date is None:
            return _fail("I couldn't understand that date. Please say it again.")

        # Speech-to-text confuses years and the model may resolve "Friday" to one that has
        # already gone. Compare against the clinic's own calendar day, not the server's.
        if preferred_date < clinic_now().date():
            return _fail("That date has already passed. Please offer a date in the future.")

        preferred_time = _parse_time(data.get("time"))
        if preferred_time is None:
            return _fail("That isn't one of our appointment times. Please offer a listed time.")

        # Same guard chain, in the same order, as the HTML booking route.
        if is_closed_day(preferred_date):
            return _fail(
                "The clinic is closed for scheduled appointments on Sundays — emergency care only."
            )
        if not is_slot_within_hours(preferred_date, preferred_time):
            return _fail("The clinic closes at 4:30 PM on Saturdays. Please offer an earlier time.")
        if is_slot_in_past(preferred_date, preferred_time):
            return _fail("That time has already passed today. Please offer a later time.")
        if not is_slot_available(preferred_date, preferred_time, doctor.id if doctor else None):
            return _fail("That time was just booked. Please offer a different slot.")

        notes = (data.get("notes") or "").strip() or None
        appointment = Appointment(
            full_name=full_name,
            email=email,
            phone=phone,
            gender=data["gender"],
            service_id=service.id,
            doctor_id=doctor.id if doctor else None,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            notes=notes[:1000] if notes else None,
        )
        db.session.add(appointment)
        db.session.commit()

        current_app.logger.info(
            "New appointment booked by voice assistant: id=%s email=%s",
            appointment.id, appointment.email,
        )

        send_appointment_confirmation(appointment)
        send_appointment_notification(appointment)

        return _ok(
            "The appointment is booked and a confirmation email is on its way.",
            appointment_id=appointment.id,
            service=service.name,
            doctor=doctor.name if doctor else "Any available dentist",
            date=preferred_date.isoformat(),
            time=preferred_time,
            # Where the patient should end up now that the booking exists. Built here rather
            # than in the browser so the URL has a single definition: the widget's page map
            # is a fixed, id-free list precisely so the model can't reach an arbitrary path,
            # and teaching it to interpolate an id would give that back.
            redirect_url=url_for("appointments.confirmation", appointment_id=appointment.id),
        )


@ns.route("/contact")
class VoiceContact(Resource):
    @ns.expect(contact_input)
    def post(self):
        """Send a message to the clinic team from a voice conversation."""
        data = ns.payload or {}

        name = (data.get("name") or "").strip()
        if len(name) < 2:
            return _fail("I need the patient's name.")

        email = (data.get("email") or "").strip().lower()
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            return _fail("That email address doesn't look right. Please confirm it.")

        body = (data.get("message") or "").strip()
        if len(body) < 5:
            return _fail("Please ask what they'd like the message to say.")

        # Shares the HTML contact form's budget, so voice isn't a way around it.
        if contact_rate_limited():
            return _fail(
                "Several messages have been sent recently. Please ask them to try again later, "
                "or give them the clinic phone number."
            )

        phone = (data.get("phone") or "").strip() or None
        subject = (data.get("subject") or "").strip() or None

        message = ContactMessage(
            name=name[:160],
            email=email[:255],
            phone=phone[:40] if phone else None,
            subject=subject[:200] if subject else None,
            message=body[:2000],
        )
        db.session.add(message)
        db.session.commit()

        current_app.logger.info(
            "Contact message sent by voice assistant: id=%s email=%s", message.id, message.email,
        )

        send_contact_notification(message)
        send_contact_autoreply(message)

        return _ok("The message has been sent to the clinic team.")
