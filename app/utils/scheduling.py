"""Clinic scheduling rules that both the booking UI and server-side validation rely on."""
from datetime import datetime, time

SATURDAY = 5  # date.weekday(): Monday is 0
SUNDAY = 6

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
