"""Flask-WTF forms for appointment booking, contact, and newsletter signup."""
from datetime import date

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length, Regexp, Optional, ValidationError

from app.models import Gender

PHONE_REGEX = r"^[\d\s\-\+\(\)]{7,20}$"

GENDER_CHOICES = [("", "Select gender")] + [(value, Gender.LABELS[value]) for value in Gender.CHOICES]

# Clinic hours are 9:00 AM – 7:00 PM with a 1:00 – 2:00 PM break, so the last bookable
# slot starts at 6:30 PM. Keep this in sync with the opening hours shown on the site.
TIME_SLOTS = [
    ("", "Select a time"),
    ("09:00 AM", "9:00 AM"),
    ("09:30 AM", "9:30 AM"),
    ("10:00 AM", "10:00 AM"),
    ("10:30 AM", "10:30 AM"),
    ("11:00 AM", "11:00 AM"),
    ("11:30 AM", "11:30 AM"),
    ("12:00 PM", "12:00 PM"),
    ("12:30 PM", "12:30 PM"),
    # 1:00 – 2:00 PM break
    ("02:00 PM", "2:00 PM"),
    ("02:30 PM", "2:30 PM"),
    ("03:00 PM", "3:00 PM"),
    ("03:30 PM", "3:30 PM"),
    ("04:00 PM", "4:00 PM"),
    ("04:30 PM", "4:30 PM"),
    ("05:00 PM", "5:00 PM"),
    ("05:30 PM", "5:30 PM"),
    ("06:00 PM", "6:00 PM"),
    ("06:30 PM", "6:30 PM"),
]


def not_in_past(form, field):
    if field.data and field.data < date.today():
        raise ValidationError("Preferred date cannot be in the past.")


class AppointmentForm(FlaskForm):
    service = SelectField("Service", validators=[DataRequired(message="Please select a service.")], coerce=int)
    doctor = SelectField("Preferred Doctor", coerce=int, validators=[Optional()])
    preferred_date = DateField("Preferred Date", validators=[DataRequired(), not_in_past])
    preferred_time = SelectField("Preferred Time", choices=TIME_SLOTS, validators=[DataRequired(message="Please select a time.")])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=160)])
    gender = SelectField("Gender", choices=GENDER_CHOICES, validators=[DataRequired(message="Please select a gender.")])
    phone = StringField("Phone Number", validators=[DataRequired(), Regexp(PHONE_REGEX, message="Enter a valid phone number.")])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=255)])
    notes = TextAreaField("Message (optional)", validators=[Optional(), Length(max=1000)])


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=160)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Regexp(PHONE_REGEX, message="Enter a valid phone number.")])
    subject = StringField("Subject", validators=[Optional(), Length(max=200)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=5, max=2000)])
    # Honeypot: hidden from real users via display:none, left blank by humans. Bots that auto-fill
    # every field populate it, so a non-empty value marks the submission as spam (checked in the
    # route). Named away from "website"/"url"/etc. — those names get targeted by browser autofill
    # even when the field is visually hidden, which caused real submissions to be dropped.
    hp_field = StringField("Leave this field empty", validators=[Optional(), Length(max=200)])


class NewsletterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
