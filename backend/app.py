import logging
import os
import socket

import psycopg
import redis
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

# Logs go to stdout. Docker captures stdout, and Loki collects it.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
)
log = logging.getLogger("backend")


def read_secret(name, default=""):
    """Read a secret from the file in NAME_FILE (Docker/Swarm secrets),
    or fall back to the NAME environment variable (Docker Compose)."""
    path = os.getenv(f"{name}_FILE")
    if path:
        with open(path) as secret_file:
            return secret_file.read().strip()
    return os.getenv(name, default)


# All configuration comes from environment variables or secret files, never hardcoded.
APP_VERSION = os.getenv("APP_VERSION", "dev")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = read_secret("DB_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = read_secret("REDIS_PASSWORD") or None

app = Flask(__name__)


def get_db():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3,
    )


def get_redis():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        socket_connect_timeout=3,
        decode_responses=True,
    )


@app.get("/api/live")
def live():
    # Liveness: the process is running and can serve HTTP. No dependency checks.
    return jsonify({"status": "alive", "version": APP_VERSION})


@app.get("/api/health")
def health():
    # Readiness: can the app actually do its job? Checks both dependencies.
    result = {"version": APP_VERSION, "container": socket.gethostname()}
    healthy = True

    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        result["postgres"] = "ok"
    except Exception as exc:
        healthy = False
        result["postgres"] = "error"
        log.error("postgres health check failed: %s", exc)

    try:
        get_redis().ping()
        result["redis"] = "ok"
    except Exception as exc:
        healthy = False
        result["redis"] = "error"
        log.error("redis health check failed: %s", exc)

    return jsonify(result), 200 if healthy else 503


@app.post("/api/visit")
def visit():
    counter = get_redis().incr("visit_counter")

    with get_db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS visits ("
            "id SERIAL PRIMARY KEY, "
            "visited_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "container TEXT)"
        )
        conn.execute(
            "INSERT INTO visits (container) VALUES (%s)",
            (socket.gethostname(),),
        )
        total = conn.execute("SELECT count(*) FROM visits").fetchone()[0]

    log.info("visit recorded redis_counter=%s db_rows=%s", counter, total)
    return jsonify({"redis_counter": counter, "db_rows": total, "version": APP_VERSION})


@app.errorhandler(Exception)
def handle_error(exc):
    if isinstance(exc, HTTPException):
        return exc
    log.exception("unhandled error")
    return jsonify({"error": str(exc)}), 500