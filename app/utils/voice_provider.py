"""Which voice backend is active, decided in one place.

The choice is made from configuration alone, so the template gate, the token endpoint and
the browser all agree without each re-deriving it from the same two config keys.

Gemini wins when both keys are present: it has a free tier, and OpenAI Realtime does not.
"""
from flask import current_app

GEMINI = "gemini"
OPENAI = "openai"


def active_provider(config=None):
    """Return GEMINI, OPENAI, or None when the assistant can't run.

    None means "no usable key", which is the signal to hide the widget rather than render a
    microphone button that cannot connect.
    """
    cfg = config or current_app.config
    if not cfg.get("VOICE_ASSISTANT_ENABLED"):
        return None
    if cfg.get("GEMINI_API_KEY"):
        return GEMINI
    if cfg.get("OPENAI_API_KEY"):
        return OPENAI
    return None
