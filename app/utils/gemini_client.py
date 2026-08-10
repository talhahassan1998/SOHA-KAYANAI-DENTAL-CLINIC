"""Gemini Live session setup for the voice assistant.

The browser holds the audio connection to Google directly over a WebSocket; this module's
only job is to mint the short-lived credential that connection is opened with, and to define
the rules and tools the session runs under.

Same reasoning as the OpenAI client it parallels: instructions and tool definitions are
attached here, server-side, via `liveConnectConstraints`. A browser can send whatever it
likes once connected, so anything defined client-side is advice, not a constraint. Pinning
them to the token means the assistant's rules — no medical advice, confirm before booking —
can't be edited away by whoever is holding the microphone.

The prompt itself is shared with the OpenAI path (`build_instructions`) because it is about
the clinic, not the vendor.
"""
import requests
from flask import current_app

from app.utils.openai_client import (
    BOOKABLE_TIMES,
    NAVIGABLE_PAGES,
    REQUEST_TIMEOUT,
    VoiceAssistantError,
    build_instructions,
)

AUTH_TOKENS_URL = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"

GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)

# The token only has to survive long enough to open the socket, so the window for starting a
# session is short even though the session itself may run longer.
TOKEN_TTL_SECONDS = 600
NEW_SESSION_TTL_SECONDS = 120


def _function_declarations():
    """The same six tools as the OpenAI path, in Gemini's schema.

    Gemini nests declarations under a `functionDeclarations` key and takes the JSON-Schema
    parameter block directly, so only the wrapper differs from `_tool_definitions()`.
    """
    from app.models import Gender

    return [
        {
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
            "name": "check_availability",
            "description": (
                "Find out which appointment times are actually free on a given date. Always "
                "call this before offering a patient a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "The date to check, as YYYY-MM-DD."},
                    "doctor_name": {
                        "type": "string",
                        "description": "Optional. Only if the patient asked for a specific dentist.",
                    },
                },
                "required": ["date"],
            },
        },
        {
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
            },
        },
        {
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
                    "doctor_name": {
                        "type": "string",
                        "description": "Omit for any available dentist.",
                    },
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "enum": BOOKABLE_TIMES},
                    "notes": {
                        "type": "string",
                        "description": "Anything the patient mentioned about symptoms or goals.",
                    },
                },
                "required": [
                    "full_name", "email", "phone", "gender", "service_name", "date", "time",
                ],
            },
        },
        {
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
            },
        },
        {
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


def _setup_config():
    """The `setup` payload, pinned to the token so the browser can't rewrite it.

    Sent as `bidiGenerateContentSetup`, not the `liveConnectConstraints` name Google's
    ephemeral-token docs use — that field doesn't exist on the v1beta REST endpoint and is
    rejected outright, in either camelCase or snake_case.
    """
    cfg = current_app.config
    return {
        "model": f"models/{cfg['GEMINI_LIVE_MODEL']}",
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": cfg["GEMINI_LIVE_VOICE"]},
                },
            },
        },
        "systemInstruction": {"parts": [{"text": build_instructions()}]},
        "tools": [{"functionDeclarations": _function_declarations()}],
        # Both directions transcribed: the patient's words drive the on-screen log, and the
        # assistant's let us show what it said without waiting for the audio to finish.
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
    }


def build_setup_message():
    """The opening frame the relay sends upstream on the browser's behalf.

    Kept here rather than in the relay so both the setup payload and the tool definitions
    have a single home.
    """
    return {"setup": _setup_config()}


# Long enough for a spoken turn, short enough that a runaway transcript can't be used to bill
# a large generation. Anything longer is truncated rather than refused.
MAX_TRANSLATE_CHARS = 1000

_TRANSLATE_PROMPT = (
    "Translate the text after the marker into English. It is one turn from a phone "
    "conversation at a dental clinic in Pakistan, so it may be Urdu, Punjabi, Pashto, "
    "Saraiki, Arabic, Roman Urdu, or already English.\n"
    "Reply with the English translation and nothing else — no quotes, no notes, no "
    "explanation, no romanisation. If it is already English, repeat it unchanged. If it is "
    "too garbled to translate, reply with exactly: ---\n\n"
    "TEXT:\n"
)


def translate_to_english(text):
    """Translate one transcript line to English for the on-screen log.

    Display only: nothing here reaches the Live session or the booking tools, so a bad
    translation can mislead a reader but can never change what gets booked. Returns None
    when there is nothing useful to show, and the caller simply omits the line.
    """
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise VoiceAssistantError("GEMINI_API_KEY is not configured")

    source = (text or "").strip()[:MAX_TRANSLATE_CHARS]
    if not source:
        return None

    model = current_app.config["GEMINI_TRANSLATE_MODEL"]
    payload = {
        "contents": [{"parts": [{"text": _TRANSLATE_PROMPT + source}]}],
        "generationConfig": {
            # Deterministic: the same transcript should not translate two different ways on
            # two different reads.
            "temperature": 0,
            "maxOutputTokens": 512,
        },
    }

    # One retry. Probing this endpoint, roughly one call in ten died on the connection rather
    # than returning anything, and a dropped line leaves a visible gap under one bubble while
    # its neighbours are translated. Retried once because the second attempt has always
    # succeeded; beyond that it isn't worth making the reader wait.
    last_error = None
    for attempt in range(2):
        try:
            response = requests.post(
                GENERATE_URL.format(model=model),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            break
        except requests.RequestException as exc:
            last_error = exc
    else:
        raise VoiceAssistantError("Could not reach Google") from last_error

    if response.status_code >= 400:
        current_app.logger.error(
            "Gemini translation failed: status=%s body=%s",
            response.status_code, response.text[:500],
        )
        raise VoiceAssistantError("Google rejected the translation request")

    candidates = (response.json() or {}).get("candidates") or []
    if not candidates:
        # Safety filters and recitation blocks both land here, with no candidate at all.
        return None

    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    translated = "".join(p.get("text", "") for p in parts).strip()

    # The model's own "couldn't translate" signal, and the degenerate cases worth hiding.
    if not translated or translated == "---":
        return None
    return translated


def mint_ephemeral_token():
    """Create a single-use credential the browser can open a Live session with.

    Returns a dict the widget needs: the token name, the socket URL, and the model.
    """
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise VoiceAssistantError("GEMINI_API_KEY is not configured")

    payload = {
        "uses": 1,
        "expireTime": _iso_in(TOKEN_TTL_SECONDS),
        "newSessionExpireTime": _iso_in(NEW_SESSION_TTL_SECONDS),
        # Everything the session may do is fixed here rather than sent from the page.
        "bidiGenerateContentSetup": _setup_config(),
    }

    try:
        response = requests.post(
            AUTH_TOKENS_URL,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise VoiceAssistantError("Could not reach Google") from exc

    if response.status_code >= 400:
        # Log the body (it explains bad keys, quota, unknown model) but never return it to
        # the browser — it can echo back configuration details.
        current_app.logger.error(
            "Gemini auth token request failed: status=%s body=%s",
            response.status_code, response.text[:500],
        )
        raise VoiceAssistantError("Google rejected the session request")

    name = (response.json() or {}).get("name")
    if not name:
        raise VoiceAssistantError("Google returned no token")

    return {
        "provider": "gemini",
        "value": name,
        "ws_url": WS_URL,
        "model": current_app.config["GEMINI_LIVE_MODEL"],
    }


def _iso_in(seconds):
    """An RFC 3339 timestamp `seconds` from now, which is the format the API expects."""
    from datetime import datetime, timedelta, timezone

    stamp = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return stamp.isoformat().replace("+00:00", "Z")
