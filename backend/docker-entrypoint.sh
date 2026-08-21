#!/bin/sh
# =====================================================================
# Backend container entrypoint.
#
# Prepares the database before handing control to the application
# server. This lives in the container layer rather than in application
# startup code so the FastAPI app itself stays unchanged and remains
# runnable outside Docker exactly as before.
#
# Environment:
#   DATABASE_URL       Connection string (required in compose).
#   WAIT_FOR_DB        Seconds to wait for the database. 0 disables.
#   RUN_MIGRATIONS     Create missing tables on start. Default true.
#   SEED_DEMO_DATA     Insert demo rows if the database is empty.
# =====================================================================
set -eu

WAIT_FOR_DB="${WAIT_FOR_DB:-60}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
SEED_DEMO_DATA="${SEED_DEMO_DATA:-false}"

log() {
    printf '%s | ENTRYPOINT | %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S')" "$1"
}

# ---------------------------------------------------------------------
# Wait for the database to accept connections.
#
# Compose already gates startup on the postgres healthcheck, but that
# only proves the server is up — not that this container can reach it.
# ---------------------------------------------------------------------
if [ "${WAIT_FOR_DB}" -gt 0 ] 2>/dev/null; then
    log "Waiting up to ${WAIT_FOR_DB}s for the database..."

    if ! python - "$WAIT_FOR_DB" <<'PY'
import sys
import time

from app.database import get_database

deadline = time.monotonic() + float(sys.argv[1])
attempt = 0

while time.monotonic() < deadline:
    attempt += 1
    if get_database().check_connection():
        print(f"Database reachable after {attempt} attempt(s).")
        sys.exit(0)
    time.sleep(2)

print("Database did not become reachable in time.", file=sys.stderr)
sys.exit(1)
PY
    then
        log "ERROR: database unreachable; refusing to start."
        exit 1
    fi
fi

# ---------------------------------------------------------------------
# Create any missing tables.
#
# `initialize()` creates tables that do not exist, then applies one
# narrow, additive, idempotent upgrade (adding track_records.run_id to
# a database that predates it, if needed — see
# app/database/migrations.py::upgrade_track_run_id_column). It does not
# alter existing tables beyond that one known case. Schema evolution
# still needs a real migration tool.
# ---------------------------------------------------------------------
if [ "${RUN_MIGRATIONS}" = "true" ]; then
    log "Ensuring database schema..."
    python -c "
import sys
from app.database import initialize
sys.exit(0 if initialize() else 1)
" || {
        log "ERROR: schema initialization failed."
        exit 1
    }
    log "Schema ready."
fi

# ---------------------------------------------------------------------
# Optional demo data. Seeding is idempotent — it skips when alerts
# already exist — so this is safe to leave enabled across restarts.
# ---------------------------------------------------------------------
if [ "${SEED_DEMO_DATA}" = "true" ]; then
    log "Seeding demo data..."
    python -m app.database.seed || log "WARNING: seeding failed; continuing."
fi

log "Starting: $*"
exec "$@"
