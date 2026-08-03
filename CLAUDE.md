# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Flask marketing website + appointment booking system + JSON REST API for a dental clinic (Soha Kayani Dental
Clinic). Server-rendered Jinja2 templates styled with Tailwind CSS via CDN (no Node/npm build step). See
README.md for the full local setup and deployment walkthrough — the essentials are below.

## Commands

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate            # Windows (this repo runs on Windows/PowerShell)
pip install -r requirements.txt
cp .env.example .env

# Database
flask db upgrade                  # apply migrations
flask db migrate -m "message"     # generate a new migration after changing app/models.py
flask seed                        # idempotent sample-data seeder (app/__init__.py registers this CLI command; logic in seed.py)

# Run
flask run                         # or: python run.py
# Site:      http://127.0.0.1:5000
# API docs:  http://127.0.0.1:5000/api/v1/docs

# Production
gunicorn -w 4 -b 0.0.0.0:8000 run:app
docker-compose up --build         # app + Postgres, runs migrations on boot
```

There is no automated test suite in this repo. Manual verification: submit `/book-appointment` or `/contact`
and check the terminal for "queued email" log lines (SMTP sends are suppressed by default via
`MAIL_SUPPRESS_SEND=True`), or POST directly to the API — see README.md's `curl` example for
`/api/v1/appointments`.

## Architecture

**Application factory + Blueprints.** `app/__init__.py`'s `create_app(config_name)` selects a config class from
`config.py` (`development` / `testing` / `production`, chosen via `FLASK_ENV`), initializes extensions from
`app/extensions.py` (`db`, `migrate`, `csrf`, `mail`, `cache`), then calls `register_blueprints`. Every
blueprint lives in its own `app/<name>/` package with an `__init__.py` that defines the `Blueprint` object and
a `routes.py` that's imported at the bottom of `__init__.py` (`from app.<name> import routes  # noqa: E402,F401`)
to attach the routes without a circular-import problem. New page sections should follow this exact pattern.

**Blueprints:** `main` (home/about/faqs/contact/newsletter/sitemap.xml/robots.txt), `appointments` (booking
form + confirmation), `services`, `doctors`, `blog` (list has `?q=` search across title/content/excerpt via
`ilike`), `gallery`, `testimonials`, and `api` (Flask-RESTX, mounted at `/api/v1`). Content-listing blueprints
(`services`, `doctors`, `blog`, `gallery`, `testimonials`) share a consistent `list` + `<slug>` detail route
shape, looking up by `slug` with `.first_or_404()`.

**REST API (`app/api/`):** Flask-RESTX `Namespace` per resource (`doctors.py`, `services.py`,
`testimonials.py`, `appointments.py`), all registered onto a single `Api` in `app/api/__init__.py` with
Swagger UI at `/api/v1/docs`. The whole `api_bp` blueprint is CSRF-exempted in `register_blueprints()` (it's
stateless JSON, not session/cookie-based) — every other blueprint keeps Flask-WTF's global CSRF protection.
API input is still fully validated server-side (namespace `fields` models, `email_validator`, manual date
parsing) even though CSRF doesn't apply.

**Models (`app/models.py`):** all SQLAlchemy models in one file, sharing a `TimestampMixin` (`created_at`).
Slugged content models (`Doctor`, `Service`, `BlogPost`) have a unique indexed `slug` column used for detail
routes. `Appointment` has `service_id` (required FK) and `doctor_id` (optional FK — "Any Available Doctor" is
`doctor_id=None`), plus a `status` column backed by the `AppointmentStatus` class constants
(`pending`/`confirmed`/`cancelled`) rather than a native enum. Changing this file requires a new Alembic
migration (`flask db migrate`).

**Forms (`app/forms.py`):** Flask-WTF `FlaskForm` classes (`AppointmentForm`, `ContactForm`,
`NewsletterForm`). `AppointmentForm.service`/`.doctor` are `SelectField`s whose `.choices` must be populated
from the DB at request time in the route handler (see `_populate_choices` in
`app/appointments/routes.py`) — they aren't set on the class. `NewsletterForm` is injected into every template
via a context processor (`inject_newsletter_form` in `app/__init__.py`), so it's always available in Jinja
without each view passing it explicitly.

**Email (`app/utils/email.py`):** `Flask-Mail` sends are dispatched on a background `threading.Thread`
(`_dispatch`) wrapped in `app.app_context()`, so request handlers (both HTML routes and the API) return
immediately without waiting on SMTP. Booking and contact flows always send two messages: one to the
patient/visitor and one to staff at `CLINIC_NOTIFY_EMAIL`. In dev, `MAIL_SUPPRESS_SEND=True` means Flask-Mail
logs instead of sending — check the terminal, not an inbox.

**Config (`config.py`):** one `Config` base class plus `DevelopmentConfig`/`TestingConfig`/`ProductionConfig`,
selected via the `config` dict keyed by `FLASK_ENV` (default `"development"`). `ProductionConfig` rewrites
`postgres://`/`postgresql://` DATABASE_URLs to `postgresql+psycopg://` (psycopg3) and wires a rotating
file handler to `logs/dental_clinic.log` in its `init_app`. All clinic contact info, social links, and mail
settings are environment-driven with defaults, then exposed to every template via the
`inject_clinic_info` context processor.

**Templates (`app/templates/`):** Jinja2 + Tailwind CSS loaded via CDN, with the custom color palette, fonts
(Poppins/Inter from Google Fonts), shadows, and animation keyframes configured inline in `base.html` — there is
no CSS build pipeline. Dark mode is a `class`-based Alpine.js + `localStorage` toggle using `dark:` variants.

## Conventions

- Route handlers commit via `db.session.add`/`db.session.commit()` directly — no repository/service layer.
- Slugs, not numeric IDs, are the public identifier in URLs for doctors/services/blog posts.
- All DB access goes through the SQLAlchemy ORM — no raw SQL.
- Secrets and per-environment values come from `.env` (via `python-dotenv`, loaded in `run.py`) — never hardcode
  clinic/SMTP/secret-key values; add new ones to `.env.example` with a safe placeholder.
