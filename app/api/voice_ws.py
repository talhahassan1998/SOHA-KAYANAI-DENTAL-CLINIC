"""WebSocket relay between the browser and Gemini Live.

Gemini's ephemeral tokens mint successfully but are rejected when the socket actually
connects (a Preview-stage limitation on Google's side, verified against both v1alpha and
v1beta). That leaves two ways for a browser to reach the Live API: ship the standing API key
to every visitor, or relay through here. We relay.

So this module exists purely to keep `GEMINI_API_KEY` on the server. It carries frames in
both directions and does not interpret them, with one exception: the browser never sends the
`setup` frame. This side does, built from the same server-side config the OpenAI path pins to
its token, so the assistant's rules can't be edited by whoever is holding the microphone.

Needs a worker that can hold a long-lived connection — the Flask dev server manages it, and
in production that means gunicorn with a gevent worker rather than the default sync one.
"""
import json
import threading

from flask import current_app, request

import websocket

from app.utils.gemini_client import WS_URL, build_setup_message
from app.utils.rate_limit import rate_limited

# Gemini closes an idle socket well before this; the cap is a backstop so a forgotten tab
# can't hold a relay (and a free-tier session slot) open indefinitely.
MAX_SESSION_SECONDS = 15 * 60


def register_voice_socket(sock, app):
    """Attach the relay route to a flask_sock.Sock instance."""

    @sock.route("/api/v1/voice/stream")
    def voice_stream(browser_ws):
        cfg = current_app.config
        api_key = cfg.get("GEMINI_API_KEY")
        if not (cfg.get("VOICE_ASSISTANT_ENABLED") and api_key):
            browser_ws.close()
            return

        # Opening a relay is what costs money, so it is counted — but on its own budget,
        # not the token endpoint's. Navigating between pages reconnects the socket several
        # times within a single conversation, and sharing one counter meant a patient who
        # browsed while talking silently ran out mid-sentence.
        #
        # A resumed socket is the same conversation carrying on after a page load, so it is
        # counted separately and far more generously. One booking can easily involve three
        # or four navigations — home to the booking page, and again to the confirmation —
        # and charging each as a new conversation exhausted the hourly allowance in a single
        # sitting. The flag comes from the browser and could be forged, which is why resumes
        # are still counted rather than waved through.
        resumed = request.args.get("resumed") == "1"
        scope = "voice-stream-resume" if resumed else "voice-stream"
        limit = cfg["VOICE_STREAM_RESUME_LIMIT"] if resumed else cfg["VOICE_STREAM_RATE_LIMIT"]
        if rate_limited(scope, limit, cfg["VOICE_TOKEN_RATE_WINDOW"]):
            browser_ws.send(json.dumps({"error": "rate_limited"}))
            browser_ws.close()
            return

        try:
            upstream = websocket.create_connection(
                f"{WS_URL}?key={api_key}", timeout=MAX_SESSION_SECONDS,
            )
        except Exception as exc:
            current_app.logger.warning("Gemini relay could not connect: %s", exc)
            browser_ws.send(json.dumps({"error": "upstream_unavailable"}))
            browser_ws.close()
            return

        logger = current_app.logger
        stop = threading.Event()

        def pump_downstream():
            """Gemini -> browser."""
            try:
                while not stop.is_set():
                    frame = upstream.recv()
                    if not frame:
                        break
                    text = frame if isinstance(frame, str) else frame.decode("utf-8", "ignore")
                    # Google reports a rejected setup — bad model id, unsupported field,
                    # exhausted quota — as an ordinary message and then closes. Swallowing it
                    # left the page sitting on "Listening…" forever with nothing to explain
                    # why, so it is logged here before being passed on.
                    if '"error"' in text or '"code"' in text:
                        logger.warning("Gemini upstream reported: %s", text[:500])
                    browser_ws.send(text)
            except Exception as exc:
                logger.info("Voice relay downstream stopped: %s", exc)
            finally:
                stop.set()
                try:
                    browser_ws.close()
                except Exception:
                    pass

        try:
            # The session config comes from here, never from the page.
            upstream.send(json.dumps(build_setup_message()))

            reader = threading.Thread(target=pump_downstream, daemon=True)
            reader.start()

            # Browser -> Gemini. Audio chunks arrive continuously, so this is the hot path.
            while not stop.is_set():
                frame = browser_ws.receive(timeout=MAX_SESSION_SECONDS)
                if frame is None:
                    break
                upstream.send(frame)
        except Exception as exc:
            logger.debug("Voice relay ended: %s", exc)
        finally:
            stop.set()
            try:
                upstream.close()
            except Exception:
                pass
