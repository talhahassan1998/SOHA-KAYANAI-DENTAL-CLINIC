# Soha Kayani Dental Clinic — Flask Dental Clinic Website

A complete, production-ready dental clinic website built with Flask: a marketing site (home, about, services,
doctors, gallery, testimonials, blog, FAQs, contact) plus an appointment booking system, a JSON REST API, and
email notifications.

## Tech Stack

- **Backend:** Python 3.12+ / Flask (application factory + Blueprints)
- **Database:** SQLAlchemy ORM — SQLite for development, PostgreSQL for production
- **Migrations:** Flask-Migrate (Alembic)
- **Forms:** Flask-WTF (CSRF-protected)
- **Email:** Flask-Mail (async dispatch via background thread)
- **REST API:** Flask-RESTX with auto-generated Swagger docs
- **Frontend:** Jinja2 + Tailwind CSS (CDN) + Alpine.js — no Node build step required
- **WSGI Server:** Gunicorn

## Project Structure

```
dental_clinic/
├── app/
│   ├── main/            # home, about, faqs, contact, newsletter, sitemap/robots
│   ├── appointments/    # booking form + confirmation
│   ├── services/        # services list/detail
│   ├── doctors/         # doctors list/detail
│   ├── blog/            # blog list/detail + search
│   ├── gallery/         # before/after gallery
│   ├── testimonials/    # patient testimonials
│   ├── api/             # Flask-RESTX REST API (/api/v1)
│   ├── utils/           # email + SEO helpers
│   ├── static/          # css, js, images
│   ├── templates/       # Jinja2 templates
│   ├── models.py        # SQLAlchemy models
│   ├── forms.py         # Flask-WTF forms
│   └── __init__.py      # application factory
├── migrations/           # Alembic migration scripts
├── seed.py               # sample data seeding script
├── config.py              # Dev/Test/Prod config classes
├── run.py                # app entrypoint
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Local Setup (Development)

1. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate    |   macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` as needed. In development you can leave `DATABASE_URL` empty (SQLite is used automatically) and
   keep `MAIL_SUPPRESS_SEND=True` so no real SMTP server is required — emails are logged instead of sent.

3. **Initialize the database**

   ```bash
   flask db upgrade
   flask seed
   ```

   `flask seed` populates doctors, services, testimonials, gallery images, blog posts and FAQs so the site
   isn't empty on first run. It is idempotent — safe to re-run.

4. **Run the development server**

   ```bash
   flask run
   # or: python run.py
   ```

   Visit `http://127.0.0.1:5000`. The REST API docs are at `http://127.0.0.1:5000/api/v1/docs`.

## Running Tests / Verifying Manually

- Book a test appointment at `/book-appointment` — check the terminal log for the "queued email" line
  (real sends are suppressed by default in dev).
- Submit the contact form at `/contact`.
- Hit the JSON API directly:

  ```bash
  curl -X POST http://127.0.0.1:5000/api/v1/appointments \
    -H "Content-Type: application/json" \
    -d '{"full_name":"Jane Doe","email":"jane@example.com","phone":"+14155550100","gender":"female","service_id":1,"preferred_date":"2026-09-01","preferred_time":"10:00 AM"}'
  ```

## Production Deployment

### Option 1: Gunicorn directly

```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://neondb_owner:npg_0XOYUs3PmKVa@ep-bitter-credit-azxxohhq-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
flask db upgrade
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

### Option 2: Docker Compose (app + PostgreSQL)

```bash
cp .env.example .env   # fill in real SMTP + secret key values
docker-compose up --build
```

This starts a Postgres container and the Flask app (via Gunicorn), running migrations automatically on boot.
The app is available at `http://localhost:8000`.

## Email Configuration

Emails are sent via Flask-Mail using SMTP credentials from `.env` (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`,
`MAIL_PASSWORD`). Set `MAIL_SUPPRESS_SEND=False` once real SMTP credentials are configured. Emails are dispatched
on a background thread so booking/contact requests aren't blocked waiting on SMTP.

## Security Notes

- CSRF protection is enabled globally for all HTML form submissions (Flask-WTF). The JSON REST API under
  `/api/v1` is exempted from CSRF (it's a stateless API, not a session-based form flow) but validates all input
  server-side.
- All database access goes through the SQLAlchemy ORM (parameterized queries — no raw SQL).
- Secrets (`SECRET_KEY`, DB credentials, SMTP credentials) are read from environment variables via `.env`,
  which is gitignored. Never commit `.env`.
- In production, set `FLASK_ENV=production` so file-based error logging (`logs/dental_clinic.log`) is enabled.

## Design System

- **Primary color:** `#0B74D1` &nbsp; **Secondary color:** `#14B8A6`
- **Fonts:** Poppins (headings) + Inter (body), loaded from Google Fonts
- Tailwind CSS is loaded via CDN with an inline config (`app/templates/base.html`) defining the custom palette,
  fonts, shadows and animation keyframes — no Node/npm build step is required to run or deploy this project.
- Dark mode is a `class`-based toggle (Alpine.js + `localStorage`), applied via `dark:` variants throughout.

## Notes on Images

All photography in the seed data and templates uses hotlinked Unsplash URLs as placeholders. Replace
`image_url` / `photo_url` fields in `seed.py` (or via the REST API / a direct DB edit) with your clinic's own
photography before going live.
