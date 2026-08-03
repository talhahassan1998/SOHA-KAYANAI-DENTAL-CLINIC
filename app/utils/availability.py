"""Appointment slot availability.

Capacity model: each time slot has as many chairs as there are doctors. A booking with a
named doctor claims that specific dentist; a "no preference" booking claims one unnamed
chair. A slot is therefore unavailable when:

  * a named doctor is requested and that doctor is already booked, or every chair is full; or
  * no preference is given and every chair is full.

Pending requests hold a chair too (so two patients can't request the same time), while
cancelled appointments release theirs.
"""
from app.models import Appointment, AppointmentStatus, Doctor

BLOCKING_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


def _bookings_by_time(preferred_date, preferred_time=None, exclude_id=None):
    """Map each time slot -> (set of booked doctor ids, count of no-preference bookings)."""
    query = Appointment.query.filter(
        Appointment.preferred_date == preferred_date,
        Appointment.status.in_(BLOCKING_STATUSES),
    )
    if preferred_time is not None:
        query = query.filter(Appointment.preferred_time == preferred_time)
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)

    slots = {}
    for time, doctor_id in query.with_entities(Appointment.preferred_time, Appointment.doctor_id):
        named, unnamed = slots.setdefault(time, (set(), 0))
        if doctor_id is None:
            slots[time] = (named, unnamed + 1)
        else:
            named.add(doctor_id)
    return slots


def _is_full(named_doctors, unnamed_count, doctor_count):
    """True when every chair in the slot is occupied."""
    return doctor_count and (len(named_doctors) + unnamed_count) >= doctor_count


def taken_times(preferred_date, doctor_id=None):
    """Return the set of time strings that can no longer be booked on this date."""
    slots = _bookings_by_time(preferred_date)
    if not slots:
        return set()

    doctor_count = Doctor.query.count()
    taken = set()
    for time, (named, unnamed) in slots.items():
        if _is_full(named, unnamed, doctor_count):
            taken.add(time)
        elif doctor_id and doctor_id in named:
            # That specific dentist is busy, though other chairs remain open.
            taken.add(time)
    return taken


def is_slot_available(preferred_date, preferred_time, doctor_id=None, exclude_id=None):
    """Server-side guard, so a booking can't be forced through by bypassing the UI."""
    slots = _bookings_by_time(preferred_date, preferred_time, exclude_id)
    named, unnamed = slots.get(preferred_time, (set(), 0))

    doctor_count = Doctor.query.count()
    if _is_full(named, unnamed, doctor_count):
        return False
    return not (doctor_id and doctor_id in named)
