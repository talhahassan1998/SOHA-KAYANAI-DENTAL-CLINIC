from flask import render_template, request, flash, redirect, url_for, jsonify, Response, current_app

from app.main import main_bp
from app.extensions import db
from app.forms import ContactForm, NewsletterForm
from app.models import (
    Doctor, Service, Testimonial, GalleryImage, FAQ, BlogPost, ContactMessage, NewsletterSubscriber
)
from app.utils.email import send_contact_notification, send_contact_autoreply
from app.utils.rate_limit import contact_rate_limited
from app.utils.seo import build_sitemap_urls


@main_bp.route("/")
def home():
    stats = [
        {"value": 10, "suffix": "+", "label": "Years Experience"},
        {"value": 15000, "suffix": "+", "label": "Happy Patients"},
        {"value": 25, "suffix": "+", "label": "Dental Specialists"},
        {"value": 5, "suffix": "-Star", "label": "Patient Reviews"},
    ]
    featured_services = Service.query.filter_by(is_featured=True).order_by(Service.display_order).limit(8).all()
    featured_doctors = Doctor.query.filter_by(is_featured=True).order_by(Doctor.display_order).limit(4).all()
    testimonials = Testimonial.query.filter_by(is_featured=True).order_by(Testimonial.display_order).limit(3).all()
    gallery_images = GalleryImage.query.order_by(GalleryImage.display_order).limit(6).all()
    faqs = FAQ.query.order_by(FAQ.display_order).limit(6).all()

    from app.forms import AppointmentForm
    appt_form = AppointmentForm()
    appt_form.service.choices = [(s.id, s.name) for s in Service.query.order_by(Service.display_order).all()]
    appt_form.doctor.choices = [(0, "Any Available Doctor")] + [
        (d.id, d.name) for d in Doctor.query.order_by(Doctor.display_order).all()
    ]

    return render_template(
        "main/home.html",
        stats=stats,
        featured_services=featured_services,
        featured_doctors=featured_doctors,
        testimonials=testimonials,
        gallery_images=gallery_images,
        faqs=faqs,
        appt_form=appt_form,
    )


@main_bp.route("/about")
def about():
    doctors = Doctor.query.order_by(Doctor.display_order).limit(4).all()
    return render_template("main/about.html", doctors=doctors)


@main_bp.route("/faqs")
def faqs():
    all_faqs = FAQ.query.order_by(FAQ.display_order).all()
    categories = sorted({f.category for f in all_faqs})
    return render_template("main/faqs.html", faqs=all_faqs, categories=categories)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        if form.hp_field.data:
            # Honeypot field was filled in — silently drop the bot submission without
            # revealing to the caller that anything was rejected.
            current_app.logger.info(
                "Contact form honeypot triggered, submission dropped: ip=%s hp_field=%r",
                request.remote_addr, form.hp_field.data,
            )
            flash("Thanks for reaching out! Our team will get back to you shortly.", "success")
            return redirect(url_for("main.contact"))

        if contact_rate_limited():
            current_app.logger.info("Contact form rate limit hit: ip=%s", request.remote_addr)
            flash("You've sent several messages recently. Please wait a bit before sending another.", "error")
            return redirect(url_for("main.contact"))

        message = ContactMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            subject=form.subject.data.strip() if form.subject.data else None,
            message=form.message.data.strip(),
        )
        db.session.add(message)
        db.session.commit()
        send_contact_notification(message)
        send_contact_autoreply(message)
        flash("Thanks for reaching out! Our team will get back to you shortly.", "success")
        return redirect(url_for("main.contact"))
    return render_template("main/contact.html", form=form)


@main_bp.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    form = NewsletterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing = NewsletterSubscriber.query.filter_by(email=email).first()
        if not existing:
            db.session.add(NewsletterSubscriber(email=email))
            db.session.commit()
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"success": True, "message": "Subscribed successfully!"})
        flash("You're subscribed to our newsletter!", "success")
        return redirect(request.referrer or url_for("main.home"))

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"success": False, "errors": form.errors}), 400
    flash("Please enter a valid email address.", "error")
    return redirect(request.referrer or url_for("main.home"))


@main_bp.route("/sitemap.xml")
def sitemap():
    urls = build_sitemap_urls()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        xml.append("<url>")
        xml.append(f"<loc>{loc}</loc>")
        if lastmod:
            xml.append(f'<lastmod>{lastmod.strftime("%Y-%m-%d")}</lastmod>')
        xml.append("</url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@main_bp.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {url_for('main.sitemap', _external=True)}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")
