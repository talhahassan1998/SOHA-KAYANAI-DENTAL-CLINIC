"""Clinic scheduling rules that both the booking UI and server-side validation rely on."""
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app

SATURDAY = 5  # date.weekday(): Monday is 0
SUNDAY = 6

DEFAULT_TIMEZONE = "Asia/Karachi"

# Saturday closes early, so its last appointment starts at 4:30 PM rather than 6:30 PM.
SATURDAY_LAST_SLOT = time(16, 30)

TIME_FORMAT = "%I:%M %p"


def is_closed_day(value):
    """Sundays are emergency care only — walk-in / phone, not online booking."""
    return value is not None and value.weekday() == SUNDAY


def _parse_slot(slot):
    """Turn a TIME_SLOTS value such as '04:30 PM' into a time, or None if unparseable."""
    try:
        return datetime.strptime(slot, TIME_FORMAT).time()
    except (TypeError, ValueError):
        return None


def is_slot_within_hours(preferred_date, preferred_time):
    """False for slots that fall outside the clinic's hours for that particular day."""
    if preferred_date is None:
        return True
    if preferred_date.weekday() != SATURDAY:
        return True

    parsed = _parse_slot(preferred_time)
    return parsed is None or parsed <= SATURDAY_LAST_SLOT


def out_of_hours_times(preferred_date, slots):
    """Slot values from `slots` that can't be booked on this date because of early closing."""
    if preferred_date is None or preferred_date.weekday() != SATURDAY:
        return set()

    unavailable = set()
    for slot in slots:
        parsed = _parse_slot(slot)
        if parsed is not None and parsed > SATURDAY_LAST_SLOT:
            unavailable.add(slot)
    return unavailable


def clinic_now():
    """Current time at the clinic.

    Read from CLINIC_TIMEZONE rather than the server's local clock: the booking form tells
    patients times are PKT, and the app is deployed in a UTC container, so a naive
    datetime.now() would keep this morning's slots bookable well into the afternoon.
    """
    name = DEFAULT_TIMEZONE
    if current_app:
        name = current_app.config.get("CLINIC_TIMEZONE") or DEFAULT_TIMEZONE

    try:
        tz = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        # A typo'd timezone shouldn't take booking down — fall back and say so once.
        if current_app:
            current_app.logger.warning(
                "Unknown CLINIC_TIMEZONE %r; falling back to %s", name, DEFAULT_TIMEZONE
            )
        tz = ZoneInfo(DEFAULT_TIMEZONE)

    return datetime.now(tz)


def is_slot_in_past(preferred_date, preferred_time, now=None):
    """True when this slot's start time has already passed (only ever true for today)."""
    if preferred_date is None:
        return False

    now = now or clinic_now()
    if preferred_date != now.date():
        return False

    parsed = _parse_slot(preferred_time)
    return parsed is not None and parsed <= now.time()


def past_times(preferred_date, slots, now=None):
    """Slot values from `slots` that have already passed, for a date that is today."""
    now = now or clinic_now()
    if preferred_date is None or preferred_date != now.date():
        return set()

    return {slot for slot in slots if is_slot_in_past(preferred_date, slot, now)}
