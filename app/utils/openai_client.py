"""OpenAI Realtime session setup for the voice assistant.

The browser holds the audio connection to OpenAI directly over WebRTC; this module's only
job is to mint the short-lived credential that connection is opened with, and to define
the rules and tools the session runs under.

Instructions and tool definitions are attached here, server-side, rather than being sent
up by the page. A browser can send whatever it likes over the data channel, so anything
defined client-side is advice, not a constraint. Pinning them to the token means the
assistant's rules — no medical advice, confirm before booking — can't be edited away by
whoever is holding the microphone.
"""
import hashlib

import requests
from flask import current_app, request

from app.forms import TIME_SLOTS
from app.models import Gender
from app.utils.scheduling import clinic_now

CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"

# The credential only has to survive the initial SDP handshake, not the whole call, so it
# expires quickly. A leaked token is then worthless within two minutes.
TOKEN_TTL_SECONDS = 120
REQUEST_TIMEOUT = 10

BOOKABLE_TIMES = [value for value, _ in TIME_SLOTS if value]

# Pages the assistant may send the patient to. A fixed list rather than a free-text URL: the
# model can't invent a path, can't send anyone off-site, and the trailing slashes (which
# differ per blueprint — /services/ has one, /book-appointment doesn't) stay correct.
NAVIGABLE_PAGES = {
    "home": "/",
    "about": "/about",
    "services": "/services/",
    "doctors": "/doctors/",
    "booking": "/book-appointment",
    "contact": "/contact",
    "gallery": "/gallery/",
    "blog": "/blog/",
    "faqs": "/faqs",
    "testimonials": "/testimonials/",
}


class VoiceAssistantError(RuntimeError):
    """Raised when a realtime session can't be created."""


def _safety_identifier():
    """A stable, non-reversible per-visitor id for OpenAI's abuse tooling.

    Hashed with the app's SECRET_KEY so it can't be reversed back to an IP address —
    OpenAI gets a way to spot one abusive visitor without us handing over the visitor.
    """
    raw = f"{current_app.config['SECRET_KEY']}:{request.remote_addr or 'unknown'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def build_instructions():
    """The assistant's system prompt, with live clinic facts baked in."""
    cfg = current_app.config
    now = clinic_now()

    return f"""You are the friendly voice receptionist for {cfg['CLINIC_NAME']}, a dental
clinic in Islamabad, Pakistan.

LANGUAGE — this matters most, and getting it wrong ruins the call:

ALWAYS SPEAK ENGLISH. English is the default and you stay in it for the whole conversation,
no matter what language the patient speaks to you in. If someone talks to you in Urdu,
Punjabi, Pashto, Hindi or Arabic, you understand them perfectly and you answer in English.
Do not mirror their language. Do not slip in Urdu words or greetings. Do not switch because
a sentence was hard to make out, and never comment on their accent or ask them to repeat
themselves in English — just understand them and reply in English.

The ONE exception: change language only if the patient directly asks you to — "speak Urdu",
"Urdu mein baat karein", "can you speak Punjabi". That is a clear instruction about the
language itself, not merely a sentence that happens to be in another language. When they ask,
switch to that language and stay in it until they ask you to change again or to go back to
English.

If they ask for Urdu, use real Urdu vocabulary rather than Hindi — "shukriya", "tashreef",
"tabdeel", "maazrat". Urdu and Hindi sound nearly identical, so if you are ever asked for one
of the two, use Urdu.

Speak naturally and warmly, the way a helpful receptionist would — not like a form.

WHAT YOU KNOW:
- Clinic: {cfg['CLINIC_NAME']}
- Phone: {cfg['CLINIC_PHONE']}
- Address: {cfg['CLINIC_ADDRESS']}
- Opening hours: Monday to Friday 9:00 AM - 7:00 PM (closed 1:00 - 2:00 PM for lunch),
  Saturday 9:00 AM - 4:30 PM, Sunday closed for scheduled visits (emergency care only —
  tell them to call {cfg['CLINIC_PHONE']}).
- Today is {now.strftime('%A, %d %B %Y')} and the local time is {now.strftime('%I:%M %p')}
  in Pakistan Standard Time. Work out "tomorrow", "next Monday" and similar from this.
- Appointments start on the half hour, from 9:00 AM to 6:30 PM.

RULES:
- Never invent prices, treatments, doctor names, or free appointment slots. Call a tool
  and use what it returns. If a tool fails, read out its message and offer the phone number.
- You are not a dentist. Do not diagnose, and do not advise on medication or treatment.
  For anything clinical say the dentist will assess it at the visit. If someone describes
  severe pain, heavy bleeding or a facial injury, tell them to call {cfg['CLINIC_PHONE']}
  right away rather than waiting for an online booking.
- Be brief to the point of blunt. One sentence is the target and two is the maximum — this
  is a spoken conversation and every extra word is a second the patient waits. Ask the next
  question directly: "What day suits you?" not "Certainly, I'd be happy to help you with
  that. Could you let me know which day would suit you best?" Skip the pleasantries, skip
  restating what they just told you, skip announcing what you are about to do. Answer, or
  ask, and stop.
- Ask for one piece of information at a time when booking. Don't read out a long list.
- Spell back the email address and phone number you heard and get a yes before using them,
  since these are easy to mishear.
- Phone numbers are the single thing speech gets wrong most often, and a long run of digits
  sometimes arrives mangled — far too many digits, or a tail of repeated zeros. A Pakistani
  mobile number is 11 digits and starts 03. If what you heard doesn't look like that, do not
  pass it to any tool and do not try to repair it yourself. Say you didn't catch it and ask
  them to say it slowly in two halves — the first five digits, then the remaining six. Read
  each half back as you get it. Never let a bad number stop the booking: everything else can
  be filled in while you sort the number out.
- Before calling book_appointment, read back the full name, phone, email, service, date and
  time together, and only continue after they clearly say yes. Same for submit_contact_form.
- You can move the patient around the site with navigate_to_page, and the conversation keeps
  going while the new page loads. Use it when they ask to see something — the treatment list,
  the dentists, photos of the clinic — and say where you're taking them as you go: "let me
  open that for you". Don't narrate it as a tool or read out the address.
- When they want to book, carry it all the way through yourself. Don't leave them with a
  filled-in form to submit — finish it. The sequence is always the same:
    1. Gather what you need, one question at a time: treatment, date, time, full name,
       phone, email, and how they'd like their gender recorded. Call check_availability
       before offering any time, and only offer times it gave you.
    2. Call fill_booking_form the moment you learn ANY of those, and again every single time
       you learn another one — after the treatment, after the date, after the name, after
       each one. Never wait until you have everything, and never call check_availability
       twice in a row without a fill_booking_form between them. Send only the fields you
       actually have; the rest can be empty, and a later call fills them in. If you find
       yourself about to ask another question without having called it, call it first.
    3. Read the whole thing back — name, phone, email, treatment, date and time — and wait
       for them to clearly agree. Never skip this: a misheard phone number or date is the
       one mistake they can't undo themselves.
    4. Once they say yes, call book_appointment. Do not ask them to press anything, and do
       not tell them to click a button — you are finishing this, not handing it back.
  If they'd rather press the button themselves, let them: fill the form and stop at step 3.
- Once book_appointment succeeds, the call is over. Their screen moves to the confirmation
  page on its own — don't call a tool for that and don't say you're opening anything. Say
  ONE closing sentence and nothing more: that it's booked, the treatment, the day and the
  time, that the confirmation email is on its way, and goodbye. Something like "That's
  booked — teeth whitening on the 15th of August at 3pm, and a confirmation email is on its
  way. Goodbye." Do not ask another question, do not offer anything further, and do not wait
  for a reply: the microphone switches off as soon as you finish that sentence, so anything
  after it is spoken to nobody.
- A message to the clinic works the same way: fill_contact_form so they can see it, read it
  back, then call submit_contact_form once they agree. Don't leave them to press Send.
- Valid appointment times are exactly: {', '.join(BOOKABLE_TIMES)}.
- Never read out internal ids, error codes, or the names of these tools."""


def _tool_definitions():
    """Function schemas for the realtime session.

    Note the assistant works in names ("Teeth Whitening"), not database ids — it can't see
    ids and shouldn't have to. The server resolves names back to rows.
    """
    return [
        {
            "type": "function",
            "name": "lookup_clinic_info",
            "description": (
                "Look up live information about the clinic: the treatments offered, the "
                "dentists and their specialties, frequently asked questions, opening hours, "
                "or contact details. Call this instead of guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": ["services", "doctors", "faqs", "hours", "contact"],
                        "description": "Which kind of information to fetch.",
                    },
                    "query": {
                        "type": "string",
                        "description": (
                            "Optional search words to narrow the results, e.g. a treatment "
                            "name or a dentist's name."
                        ),
                    },
                },
                "required": ["topic"],
            },
        },
        {
            "type": "function",
            "name": "check_availability",
            "description": (
                "Find out which appointment times are actually free on a given date. Always "
                "call this before offering a patient a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date to check, as YYYY-MM-DD.",
                    },
                    "doctor_name": {
                        "type": "string",
                        "description": "Optional. Only if the patient asked for a specific dentist.",
                    },
                },
                "required": ["date"],
            },
        },
        {
            "type": "function",
            "name": "navigate_to_page",
            "description": (
                "Open one of the clinic's pages in the patient's browser. Use this when they "
                "ask to see something that lives on another page, or before filling in a "
                "form they aren't currently looking at. Tell them where you're taking them "
                "as you do it. The conversation continues while the page loads."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "enum": sorted(NAVIGABLE_PAGES),
                        "description": "Which page to open.",
                    },
                },
                "required": ["page"],
            },
        },
        {
            "type": "function",
            "name": "fill_booking_form",
            "description": (
                "Fill in the appointment form on the page in front of the patient so they can "
                "watch the details go in. Opens the booking page first if they aren't on it. "
                "Send only the fields you have confirmed. This does not book anything — call "
                "book_appointment once they agree to finish it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "gender": {"type": "string", "enum": Gender.CHOICES},
                    "service_name": {"type": "string", "description": "The treatment, by name."},
                    "doctor_name": {"type": "string", "description": "Omit for no preference."},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "enum": BOOKABLE_TIMES},
                    "notes": {"type": "string"},
                },
                "required": [],
            },
        },
        {
            "type": "function",
            "name": "book_appointment",
            "description": (
                "Actually book the appointment and email the confirmation. The patient is "
                "taken to their confirmation page automatically once this succeeds. Only "
                "call this after reading every detail back to the patient and hearing them "
                "agree."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "gender": {"type": "string", "enum": Gender.CHOICES},
                    "service_name": {"type": "string", "description": "The treatment, by name."},
                    "doctor_name": {"type": "string", "description": "Omit for any available dentist."},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "enum": BOOKABLE_TIMES},
                    "notes": {"type": "string", "description": "Anything the patient mentioned about symptoms or goals."},
                },
                "required": ["full_name", "email", "phone", "gender", "service_name", "date", "time"],
            },
        },
        {
            "type": "function",
            "name": "fill_contact_form",
            "description": (
                "Fill in the contact form on the page so the patient can review it. Use this "
                "when they are on the contact page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "subject": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": [],
            },
        },
        {
            "type": "function",
            "name": "submit_contact_form",
            "description": (
                "Send a message to the clinic team on the patient's behalf. Only call this "
                "after reading the message back and hearing them agree."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "subject": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["name", "email", "message"],
            },
        },
    ]


def mint_client_secret():
    """Create an ephemeral credential the browser can open a realtime session with.

    Returns the raw JSON from OpenAI; the browser needs its `value`.
    """
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise VoiceAssistantError("OPENAI_API_KEY is not configured")

    payload = {
        "expires_after": {"anchor": "created_at", "seconds": TOKEN_TTL_SECONDS},
        "session": {
            "type": "realtime",
            "model": current_app.config["OPENAI_REALTIME_MODEL"],
            "instructions": build_instructions(),
            "audio": {
                "output": {"voice": current_app.config["OPENAI_REALTIME_VOICE"]},
            },
            "tools": _tool_definitions(),
            "tool_choice": "auto",
        },
    }

    try:
        response = requests.post(
            CLIENT_SECRETS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "OpenAI-Safety-Identifier": _safety_identifier(),
            },
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise VoiceAssistantError("Could not reach OpenAI") from exc

    if response.status_code >= 400:
        # Log the body (it explains bad keys, quota, unknown model) but never return it to
        # the browser — it can echo back configuration details.
        current_app.logger.error(
            "OpenAI client secret request failed: status=%s body=%s",
            response.status_code, response.text[:500],
        )
        raise VoiceAssistantError("OpenAI rejected the session request")

    return response.json()
