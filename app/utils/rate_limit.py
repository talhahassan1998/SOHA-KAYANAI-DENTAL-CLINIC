"""Per-IP rate limiting for endpoints that are cheap to call and expensive to serve.

Backed by Flask-Caching. Note CACHE_TYPE is "SimpleCache", which is per-process: under
gunicorn's default 4 sync workers the effective allowance is the limit times the worker
count. That's fine for the abuse this guards against (a visitor hammering a form or
burning API credit), but it isn't a hard quota — swap in Redis if you ever need one.
"""
import time

from flask import request

from app.extensions import cache


def rate_limited(scope, limit, window):
    """True when this caller has already used up `limit` requests in `window` seconds.

    Counts the current request when it returns False, so call this once per request and
    only on the path that actually does the work.

    The window runs from the caller's first request and is not extended by later ones. It
    used to be: every accepted request re-set the TTL, which turned a fixed window into a
    sliding one, so a steady caller's allowance never reset and reaching the limit meant
    waiting out the full window in silence rather than from when they started.
    """
    key = f"{scope}-rate:{request.remote_addr}"
    entry = cache.get(key)

    if entry is None:
        # First request in this window: the expiry is pinned here and left alone afterwards.
        cache.set(key, (1, time.time() + window), timeout=window)
        return False

    count, expires_at = entry
    if time.time() >= expires_at:
        # SimpleCache should have dropped it, but a clock that has moved or a backend that
        # keeps entries a little longer shouldn't cost the caller their reset.
        cache.set(key, (1, time.time() + window), timeout=window)
        return False

    if count >= limit:
        return True

    remaining = max(int(expires_at - time.time()), 1)
    cache.set(key, (count + 1, expires_at), timeout=remaining)
    return False


CONTACT_RATE_LIMIT = 5           # max submissions...
CONTACT_RATE_WINDOW = 60 * 10    # ...per 10 minutes, per IP


def contact_rate_limited():
    """Shared by the HTML contact form and the voice assistant's submit tool, so speaking
    to the assistant can't be used to sidestep the form's own limit."""
    return rate_limited("contact", CONTACT_RATE_LIMIT, CONTACT_RATE_WINDOW)

