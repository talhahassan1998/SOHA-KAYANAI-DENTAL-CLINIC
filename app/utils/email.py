# """Email sending helpers, dispatched on a background thread so requests don't block on SMTP."""
# import threading

# from flask import current_app, render_template, url_for
# from flask_mail import Message

# from app.extensions import mail
# from app.utils.tokens import generate_confirm_token, generate_cancel_token


# def _send_async(app, msg):
#     with app.app_context():
#         try:
#             mail.send(msg)
#         except Exception:
#             app.logger.exception("Failed to send email: %s", msg.subject)


# def _dispatch(msg):
#     app = current_app._get_current_object()
#     thread = threading.Thread(target=_send_async, args=(app, msg))
#     thread.start()
#     return thread


# def send_appointment_confirmation(appointment):
#     """Email the patient confirming their appointment request was received."""
#     msg = Message(
#         subject=f"Appointment Request Received — {current_app.config['CLINIC_NAME']}",
#         recipients=[appointment.email],
#         html=render_template("emails/appointment_confirmation.html", appointment=appointment),
#     )
#     current_app.logger.info("Queued appointment confirmation email to %s", appointment.email)
#     return _dispatch(msg)


# def send_appointment_notification(appointment):
#     """Notify clinic staff of a new appointment request, with a one-click confirm link."""
#     notify_email = current_app.config["CLINIC_NOTIFY_EMAIL"]
#     confirm_url = url_for("appointments.confirm", token=generate_confirm_token(appointment.id), _external=True)
#     cancel_url = url_for("appointments.cancel", token=generate_cancel_token(appointment.id), _external=True)
#     msg = Message(
#         subject=f"New Appointment Request — {appointment.full_name}",
#         recipients=[notify_email],
#         html=render_template(
#             "emails/appointment_notification.html",
#             appointment=appointment,
#             confirm_url=confirm_url,
#             cancel_url=cancel_url,
#         ),
#     )
#     return _dispatch(msg)


# def send_appointment_confirmed(appointment):
#     """Notify the patient that the clinic has confirmed their appointment."""
#     msg = Message(
#         subject=f"Appointment Confirmed — {current_app.config['CLINIC_NAME']}",
#         recipients=[appointment.email],
#         html=render_template("emails/appointment_confirmed.html", appointment=appointment),
#     )
#     current_app.logger.info("Queued appointment confirmed email to %s", appointment.email)
#     return _dispatch(msg)


# def send_appointment_cancelled(appointment):
#     """Let the patient know their appointment request was cancelled by the clinic."""
#     msg = Message(
#         subject=f"Appointment Request Cancelled — {current_app.config['CLINIC_NAME']}",
#         recipients=[appointment.email],
#         html=render_template("emails/appointment_cancelled.html", appointment=appointment),
#     )
#     current_app.logger.info("Queued appointment cancelled email to %s", appointment.email)
#     return _dispatch(msg)


# def send_contact_notification(contact_message):
#     """Notify clinic staff of a new contact form submission."""
#     notify_email = current_app.config["CLINIC_NOTIFY_EMAIL"]
#     msg = Message(
#         subject=f"New Contact Message — {contact_message.subject or 'Website Inquiry'}",
#         recipients=[notify_email],
#         html=render_template("emails/contact_notification.html", contact_message=contact_message),
#     )
#     return _dispatch(msg)


# def send_contact_autoreply(contact_message):
#     """Confirm to the sender that their contact form message was received."""
#     msg = Message(
#         subject=f"We've received your message — {current_app.config['CLINIC_NAME']}",
#         recipients=[contact_message.email],
#         html=render_template("emails/contact_autoreply.html", contact_message=contact_message),
#     )
#     current_app.logger.info("Queued contact autoreply email to %s", contact_message.email)
#     return _dispatch(msg)


"""Email sending helpers using Resend HTTPS API."""

import os
import resend

from flask import current_app, render_template, url_for

from app.utils.tokens import generate_confirm_token, generate_cancel_token


def _send_email(subject, recipients, html):
    """Send an email through Resend's HTTPS API."""

    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        current_app.logger.error(
            "RESEND_API_KEY is not configured"
        )
        return False

    # Use your existing MAIL_DEFAULT_SENDER variable.
    sender = (
        current_app.config.get("MAIL_DEFAULT_SENDER")
        or os.getenv("MAIL_DEFAULT_SENDER")
        or os.getenv("MAIL_USERNAME")
    )

    if not sender:
        current_app.logger.error(
            "MAIL_DEFAULT_SENDER / MAIL_USERNAME is not configured"
        )
        return False

    try:
        resend.api_key = api_key

        current_app.logger.info(
            "Resend: sending email to %s",
            recipients
        )

        result = resend.Emails.send({
            "from": sender,
            "to": recipients,
            "subject": subject,
            "html": html,
        })

        current_app.logger.info(
            "Resend: email sent successfully: %s | %s",
            subject,
            result,
        )

        return True

    except Exception:
        current_app.logger.exception(
            "Resend: failed to send email: %s",
            subject,
        )
        return False


def send_appointment_confirmation(appointment):
    """Email the patient confirming their appointment request was received."""

    subject = (
        f"Appointment Request Received — "
        f"{current_app.config['CLINIC_NAME']}"
    )

    html = render_template(
        "emails/appointment_confirmation.html",
        appointment=appointment,
    )

    current_app.logger.info(
        "Sending appointment confirmation email to %s",
        appointment.email,
    )

    return _send_email(
        subject=subject,
        recipients=[appointment.email],
        html=html,
    )


def send_appointment_notification(appointment):
    """Notify clinic staff of a new appointment request."""

    notify_email = current_app.config["CLINIC_NOTIFY_EMAIL"]

    confirm_url = url_for(
        "appointments.confirm",
        token=generate_confirm_token(appointment.id),
        _external=True,
    )

    cancel_url = url_for(
        "appointments.cancel",
        token=generate_cancel_token(appointment.id),
        _external=True,
    )

    subject = f"New Appointment Request — {appointment.full_name}"

    html = render_template(
        "emails/appointment_notification.html",
        appointment=appointment,
        confirm_url=confirm_url,
        cancel_url=cancel_url,
    )

    current_app.logger.info(
        "Sending appointment notification to %s",
        notify_email,
    )

    return _send_email(
        subject=subject,
        recipients=[notify_email],
        html=html,
    )


def send_appointment_confirmed(appointment):
    """Notify the patient that the clinic has confirmed their appointment."""

    subject = (
        f"Appointment Confirmed — "
        f"{current_app.config['CLINIC_NAME']}"
    )

    html = render_template(
        "emails/appointment_confirmed.html",
        appointment=appointment,
    )

    current_app.logger.info(
        "Sending appointment confirmed email to %s",
        appointment.email,
    )

    return _send_email(
        subject=subject,
        recipients=[appointment.email],
        html=html,
    )


def send_appointment_cancelled(appointment):
    """Let the patient know their appointment request was cancelled."""

    subject = (
        f"Appointment Request Cancelled — "
        f"{current_app.config['CLINIC_NAME']}"
    )

    html = render_template(
        "emails/appointment_cancelled.html",
        appointment=appointment,
    )

    current_app.logger.info(
        "Sending appointment cancelled email to %s",
        appointment.email,
    )

    return _send_email(
        subject=subject,
        recipients=[appointment.email],
        html=html,
    )


def send_contact_notification(contact_message):
    """Notify clinic staff of a new contact form submission."""

    notify_email = current_app.config["CLINIC_NOTIFY_EMAIL"]

    subject = (
        f"New Contact Message — "
        f"{contact_message.subject or 'Website Inquiry'}"
    )

    html = render_template(
        "emails/contact_notification.html",
        contact_message=contact_message,
    )

    current_app.logger.info(
        "Sending contact notification to %s",
        notify_email,
    )

    return _send_email(
        subject=subject,
        recipients=[notify_email],
        html=html,
    )


def send_contact_autoreply(contact_message):
    """Confirm to the sender that their contact form message was received."""

    subject = (
        f"We've received your message — "
        f"{current_app.config['CLINIC_NAME']}"
    )

    html = render_template(
        "emails/contact_autoreply.html",
        contact_message=contact_message,
    )

    current_app.logger.info(
        "Sending contact autoreply to %s",
        contact_message.email,
    )

    return _send_email(
        subject=subject,
        recipients=[contact_message.email],
        html=html,
    )
