"""Helpers for generating sitemap.xml and robots.txt content."""
from flask import url_for

STATIC_ENDPOINTS = [
    "main.home",
    "main.about",
    "main.faqs",
    "main.contact",
    "services.list_services",
    "doctors.list_doctors",
    "gallery.index",
    "testimonials.index",
    "blog.list_posts",
    "appointments.book",
]


def build_sitemap_urls():
    """Return a list of (loc, lastmod) tuples for the sitemap."""
    from app.models import BlogPost, Service, Doctor

    urls = []
    for endpoint in STATIC_ENDPOINTS:
        urls.append((url_for(endpoint, _external=True), None))

    for service in Service.query.all():
        urls.append((url_for("services.detail", slug=service.slug, _external=True), service.created_at))

    for doctor in Doctor.query.all():
        urls.append((url_for("doctors.detail", slug=doctor.slug, _external=True), doctor.created_at))

    for post in BlogPost.query.filter_by(is_published=True).all():
        urls.append((url_for("blog.detail", slug=post.slug, _external=True), post.published_at))

    return urls
