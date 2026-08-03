---
name: run-dentalclinic
description: Build, run, and drive the Soha Kayani Dental Clinic Flask app. Use when asked to start the app, run it, take a screenshot of a page, verify the booking flow, hit the REST API, or confirm a code change works in the real running app (not just by reading code).
---

Server-rendered Flask app (Jinja2 + Tailwind CDN, no JS build step) plus a
Flask-RESTX JSON API at `/api/v1`. Driven two ways: `smoke.sh` (curl —
fast, no browser, covers pages + API + a real appointment booking) and
`browser_smoke.js` (Playwright — proves the actual HTML form + CSRF flow
in a real browser, produces screenshots). Start with `smoke.sh`; reach for
`browser_smoke.js` when the change touches templates/CSS/JS and you need
visual proof.

All paths below are relative to the repo root (`d:\dentalclinic`), run
from a shell already `cd`'d there. Commands shown were run via bash
(Git Bash / MSYS on this Windows box); PowerShell equivalents are noted
where the syntax actually differs.

## Prerequisites

A `.venv` with dependencies installed (this repo ships one already):

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env        # if .env doesn't exist yet
```

For the browser driver only: Node.js (already on PATH in this
environment) plus Playwright + a Chromium build, installed once into the
skill directory itself:

```bash
cd .claude/skills/run-dentalclinic
npm install playwright --no-save
npx playwright install chromium chromium-headless-shell
```

Both browser pieces are required — `chromium.launch()`'s default
`headless: true` needs `chromium-headless-shell`, not just the full
`chromium` build (see Gotchas). This downloads to
`%LOCALAPPDATA%\ms-playwright\` (~300MB total, one-time); `node_modules`
here is already populated so this step is skippable unless it's missing.

## Setup

```bash
.venv/Scripts/flask.exe db upgrade    # apply migrations (idempotent)
```

## Run (agent path)

### 1. `smoke.sh` — primary, fast, no browser needed

```bash
bash .claude/skills/run-dentalclinic/smoke.sh
```

It starts the server with `flask run --no-reload` (a single process —
see Gotchas for why plain `python run.py` is worse for scripting on
Windows), waits for it to answer, then:

- GETs every page route (`/`, `/services/`, `/doctors/`, `/blog/`,
  `/gallery/`, `/testimonials/`, `/faqs`, `/contact`,
  `/book-appointment`, `/api/v1/docs`) and checks for 200
- GETs `/api/v1/doctors` and `/api/v1/services` and checks for real records
- **POSTs a real appointment** to `/api/v1/appointments` and checks for 201
- greps the server log for the "Queued appointment confirmation email"
  line (the manual-verification step CLAUDE.md describes, automated)

Prints `PASS`/`FAIL` per step, exits non-zero on any failure, and prints
the Windows PID + `taskkill` command to stop the server at the end:

```
PASS: server up at http://127.0.0.1:5000 (log: /tmp/dentalclinic_smoke/server.log)
PASS: GET / -> 200
...
PASS: POST /api/v1/appointments -> 201 (id=7 status=pending)
PASS: confirmation email queued (see /tmp/dentalclinic_smoke/server.log)

All smoke checks passed.
Server PID (Windows): 7384 — stop with: taskkill //F //PID 7384
```

If a server is already listening on the port, it reuses it (and doesn't
print a PID — it wasn't the one that started it, so don't kill it).

Server log: `${TMPDIR:-/tmp}/dentalclinic_smoke/server.log` (on this box,
`C:\Users\<user>\AppData\Local\Temp\dentalclinic_smoke\server.log`).

### 2. `browser_smoke.js` — visual proof, real browser

Requires the server already running (start it with `smoke.sh` first, or
by hand — see below). Then:

```bash
node .claude/skills/run-dentalclinic/browser_smoke.js
```

It loads the home page (scrolling through it first — see Gotchas),
screenshots it, then drives the actual `/book-appointment` HTML form
(fills name/email/phone/service/date/time, clicks submit, follows the
CSRF-protected POST) and screenshots the result. Exits 0 and prints
`PASS: booking flow reached confirmation page` if the redirect to
`/book-appointment/confirmation/<id>` happened; exits 1 otherwise.

Screenshots land in `.claude/skills/run-dentalclinic/shots/`:

| file | what it shows |
|---|---|
| `01-home.png` | home page, full page, after scrolling to trigger reveal/counter animations |
| `02-book-form.png` | the booking form before submission |
| `03-book-result.png` | the "Thank you" confirmation page after a real POST |

Override target/output with env vars: `BASE=http://127.0.0.1:5001 OUT=/tmp/shots node .claude/skills/run-dentalclinic/browser_smoke.js`.

### Stopping the server

```bash
pid=$(netstat -ano | grep ":5000 " | grep LISTENING | awk '{print $NF}' | head -1)
taskkill //F //PID $pid
```

(`$!` from a backgrounded `flask run` is unreliable to kill by on this
Windows/Git-Bash setup — go by the port's actual listening PID instead,
which `smoke.sh` already prints for you.)

## Run (human path)

```bash
.venv/Scripts/flask run           # http://127.0.0.1:5000, Ctrl-C to stop
```

Debug mode is on by default in dev (`DevelopmentConfig.DEBUG = True`),
so this spawns a Werkzeug reloader child process — fine interactively,
just don't script against its PID (see Gotchas).

## Test

No automated test suite in this repo (per CLAUDE.md) — `smoke.sh` and
`browser_smoke.js` are the verification path.

---

## Gotchas

- **Trailing slashes are inconsistent across blueprints.** `/services`,
  `/doctors`, `/blog`, `/gallery`, `/testimonials` 308-redirect to a
  trailing-slash form (`Blueprint(..., url_prefix=...)` list routes are
  registered as `""` under a prefix that Flask normalizes). But
  `/book-appointment`, `/faqs`, `/contact` have **no** trailing slash and
  404 if you add one — its blueprint route is `@appointments_bp.route("")`
  with no prefix-level slash handling. Don't assume one pattern; `smoke.sh`
  hits the exact paths that return 200 directly.
- **`python run.py` / plain `flask run` spawn a reloader child** because
  `DevelopmentConfig.DEBUG = True`, leaving two `python.exe` processes on
  Windows and no single PID that owns the port. Use
  `flask run --no-reload` for anything you intend to kill by PID
  (`smoke.sh` already does this); go by the port's listening PID via
  `netstat -ano`, not `$!`.
- **Home page stats and scroll-reveal sections render as `0+` / blank on
  a naive screenshot.** `app/static/js/main.js` animates `[data-counter]`
  spans and reveals `.reveal`-class sections via `IntersectionObserver`
  — they only fire once the element scrolls into the viewport. A
  `fullPage: true` screenshot taken right after `goto()` without
  scrolling captures every below-the-fold section still at its initial
  `0` / hidden state. `browser_smoke.js` scrolls the page in 400px steps
  before screenshotting to trigger these.
- **Playwright's default `headless: true` needs the separate
  `chromium-headless-shell` package**, not just `chromium` — running only
  `npx playwright install chromium` downloads the full Chrome-for-Testing
  browser but leaves `chromium.launch()` failing with "Executable doesn't
  exist ... chrome-headless-shell.exe" until you also run
  `npx playwright install chromium-headless-shell`.
- **`AppointmentForm.service`/`.doctor` choices are populated per-request**
  in the route handler, not on the form class — if you're driving the
  HTML form and it 500s on load, check `_populate_choices` in
  `app/appointments/routes.py` before assuming the form itself is broken.
- **The API's `send_appointment_notification` (staff email) doesn't log
  an explicit "Queued" line** the way `send_appointment_confirmation`
  (patient email) does — only the patient-facing one shows up as
  `grep`-able evidence in the server log, even though both are sent (see
  `app/utils/email.py`). Don't treat the notification email's silence in
  the log as a failure.

## Troubleshooting

- **`curl: (7) Failed to connect`** when `smoke.sh` polls the server:
  usually a stale process is already bound to port 5000 without actually
  serving (e.g. a previous debug-mode reloader child left running). Check
  `netstat -ano | grep ":5000 "` for extra `python.exe` PIDs and
  `taskkill //F //PID <pid>` each one, then rerun.
- **`Error: Cannot find module 'playwright'`** running `browser_smoke.js`:
  the skill directory's own `node_modules` is missing — rerun
  `npm install playwright --no-save` from `.claude/skills/run-dentalclinic`.
- **`browserType.launch: Executable doesn't exist at ...chrome-headless-shell.exe`**:
  see the Playwright gotcha above — run
  `npx playwright install chromium-headless-shell`.
