#!/usr/bin/env bash
# Curl-based smoke test for the dental clinic Flask app.
# Starts the dev server (flask run --no-reload, so it's a single process —
# the normal `python run.py` / `flask run` path spawns a Werkzeug reloader
# child because DevelopmentConfig.DEBUG=True, which leaves two python.exe
# processes and no single PID to kill cleanly on Windows), waits for it to
# answer, exercises the public pages + REST API, books a real appointment
# through the API, and greps the log for the "queued email" line CLAUDE.md
# says to check. Prints PASS/FAIL per step and exits non-zero on failure.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

PORT="${PORT:-5000}"
BASE="http://127.0.0.1:${PORT}"
LOG_DIR="${TMPDIR:-/tmp}/dentalclinic_smoke"
mkdir -p "$LOG_DIR"
SERVER_LOG="$LOG_DIR/server.log"

PY="$REPO_ROOT/.venv/Scripts/python.exe"
FLASK="$REPO_ROOT/.venv/Scripts/flask.exe"

fail() { echo "FAIL: $1"; exit 1; }
pass() { echo "PASS: $1"; }

[ -x "$PY" ] || fail ".venv not found — run: python -m venv .venv && .venv/Scripts/pip install -r requirements.txt"
[ -f "$REPO_ROOT/.env" ] || fail ".env not found — run: cp .env.example .env"

# --- start server (single process; no reloader) ---------------------------
already_running=0
if curl -sf -o /dev/null "$BASE/" 2>/dev/null; then
  already_running=1
  echo "server already running on :$PORT, reusing it"
else
  : > "$SERVER_LOG"
  FLASK_APP=run.py "$FLASK" run --no-reload --host 127.0.0.1 --port "$PORT" \
    > "$SERVER_LOG" 2>&1 &
  for i in $(seq 1 30); do
    curl -sf -o /dev/null "$BASE/" 2>/dev/null && break
    sleep 1
  done
  curl -sf -o /dev/null "$BASE/" || { cat "$SERVER_LOG"; fail "server did not come up within 30s (see $SERVER_LOG)"; }
fi
pass "server up at $BASE (log: $SERVER_LOG)"

# --- page smoke: note the trailing-slash split (see Gotchas) --------------
declare -A pages=(
  ["/"]=200
  ["/services/"]=200
  ["/doctors/"]=200
  ["/blog/"]=200
  ["/gallery/"]=200
  ["/testimonials/"]=200
  ["/faqs"]=200
  ["/contact"]=200
  ["/book-appointment"]=200
  ["/api/v1/docs"]=200
)
for path in "${!pages[@]}"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path")
  [ "$code" = "${pages[$path]}" ] && pass "GET $path -> $code" || fail "GET $path -> $code (expected ${pages[$path]})"
done

# --- API smoke: read endpoints ---------------------------------------------
doctors_json=$(curl -sf "$BASE/api/v1/doctors")
echo "$doctors_json" | grep -q '"slug"' || fail "GET /api/v1/doctors did not return doctor records"
pass "GET /api/v1/doctors returned records"

services_json=$(curl -sf "$BASE/api/v1/services")
service_id=$(echo "$services_json" | "$PY" -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
[ -n "$service_id" ] || fail "could not read a service_id from /api/v1/services"
pass "GET /api/v1/services returned service_id=$service_id"

# --- API smoke: book an appointment (real end-to-end write) ---------------
future_date=$("$PY" -c "import datetime; print((datetime.date.today()+datetime.timedelta(days=14)).isoformat())")
resp=$(curl -s -w '\n%{http_code}' -X POST "$BASE/api/v1/appointments" \
  -H "Content-Type: application/json" \
  -d "{\"full_name\":\"Smoke Test\",\"email\":\"smoke@example.com\",\"phone\":\"03001234567\",\"service_id\":$service_id,\"preferred_date\":\"$future_date\",\"preferred_time\":\"11:00\"}")
code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')
[ "$code" = "201" ] || { echo "$body"; fail "POST /api/v1/appointments -> $code (expected 201)"; }
pass "POST /api/v1/appointments -> 201 ($(echo "$body" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(f\"id={d['id']} status={d['status']}\")"))"

sleep 1  # email is sent on a background thread — give it a moment to log
grep -q "Queued appointment confirmation email" "$SERVER_LOG" && \
  pass "confirmation email queued (see $SERVER_LOG)" || \
  echo "NOTE: no 'Queued appointment confirmation email' line found in $SERVER_LOG yet"

echo
echo "All smoke checks passed."
if [ "$already_running" = 0 ]; then
  pid=$(netstat -ano | grep ":$PORT " | grep LISTENING | awk '{print $NF}' | head -1)
  echo "Server PID (Windows): $pid — stop with: taskkill //F //PID $pid"
else
  echo "Server was already running before this script — left it running."
fi
