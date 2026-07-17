"""TemberaGo — Flask backend for tourism & transport bookings."""

import logging
import os
import re
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "temberago.db"

# ---------------------------------------------------------------------------
# Company config (read once at startup)
# ---------------------------------------------------------------------------
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+250 788 438 076")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "info@temberago.com")
WHATSAPP = os.getenv("WHATSAPP_NUMBER", "250788523999")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me-in-production")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name   TEXT NOT NULL,
                phone       TEXT NOT NULL,
                email       TEXT NOT NULL,
                country     TEXT,
                service     TEXT NOT NULL,
                vehicle     TEXT,
                pickup      TEXT NOT NULL,
                destination TEXT,
                travel_date TEXT NOT NULL,
                guests      TEXT,
                notes       TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL,
                subject    TEXT NOT NULL,
                message    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quick_quotes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                service     TEXT NOT NULL,
                origin      TEXT NOT NULL,
                destination TEXT NOT NULL,
                travel_date TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
            """
        )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))


def validate_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value or "")
    return len(digits) >= 7


# ---------------------------------------------------------------------------
# Email notification
# ---------------------------------------------------------------------------

def send_notification(subject: str, body: str) -> None:
    """Send email notification. Silently skips when SMTP is not configured."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL]):
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        log.info("Notification sent: %s", subject)
    except Exception as exc:
        log.warning("Failed to send notification '%s': %s", subject, exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        company_phone=COMPANY_PHONE,
        company_email=COMPANY_EMAIL,
        whatsapp=WHATSAPP,
    )


@app.route("/api/booking", methods=["POST"])
def api_booking():
    data = request.get_json(silent=True) or {}

    required = ["full_name", "phone", "email", "service", "pickup", "travel_date"]
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing required fields: {', '.join(missing)}"}), 400

    if not validate_email(data["email"]):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    if not validate_phone(data["phone"]):
        return jsonify({"ok": False, "error": "Please enter a valid phone number."}), 400

    record = {
        "full_name":   data["full_name"].strip(),
        "phone":       data["phone"].strip(),
        "email":       data["email"].strip().lower(),
        "country":     (data.get("country") or "").strip(),
        "service":     data["service"].strip(),
        "vehicle":     (data.get("vehicle") or "").strip(),
        "pickup":      data["pickup"].strip(),
        "destination": (data.get("destination") or "").strip(),
        "travel_date": data["travel_date"].strip(),
        "guests":      (data.get("guests") or "1").strip(),
        "notes":       (data.get("notes") or "").strip(),
        "created_at":  datetime.utcnow().isoformat(),
    }

    try:
        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO bookings (
                    full_name, phone, email, country, service, vehicle,
                    pickup, destination, travel_date, guests, notes, created_at
                ) VALUES (
                    :full_name, :phone, :email, :country, :service, :vehicle,
                    :pickup, :destination, :travel_date, :guests, :notes, :created_at
                )
                """,
                record,
            )
            booking_id = cur.lastrowid
    except sqlite3.Error as exc:
        log.error("DB error saving booking: %s", exc)
        return jsonify({"ok": False, "error": "Failed to save booking. Please try again."}), 500

    body = (
        f"New booking request #{booking_id}\n\n"
        f"Name: {record['full_name']}\n"
        f"Phone: {record['phone']}\n"
        f"Email: {record['email']}\n"
        f"Country: {record['country'] or '—'}\n"
        f"Service: {record['service']}\n"
        f"Vehicle: {record['vehicle'] or 'Any'}\n"
        f"Pickup: {record['pickup']}\n"
        f"Destination: {record['destination'] or '—'}\n"
        f"Date: {record['travel_date']}\n"
        f"Guests: {record['guests']}\n"
        f"Notes: {record['notes'] or '—'}\n"
    )
    send_notification(f"TemberaGo Booking #{booking_id}", body)
    log.info("Booking saved: #%d (%s)", booking_id, record["email"])

    return jsonify({
        "ok": True,
        "message": "Your request was received. We'll contact you within 2 hours.",
        "id": booking_id,
    })


@app.route("/api/contact", methods=["POST"])
def api_contact():
    data = request.get_json(silent=True) or {}

    required = ["name", "email", "subject", "message"]
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing required fields: {', '.join(missing)}"}), 400

    if not validate_email(data["email"]):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    record = {
        "name":       data["name"].strip(),
        "email":      data["email"].strip().lower(),
        "subject":    data["subject"].strip(),
        "message":    data["message"].strip(),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO contacts (name, email, subject, message, created_at) "
                "VALUES (:name, :email, :subject, :message, :created_at)",
                record,
            )
            contact_id = cur.lastrowid
    except sqlite3.Error as exc:
        log.error("DB error saving contact: %s", exc)
        return jsonify({"ok": False, "error": "Failed to save message. Please try again."}), 500

    body = (
        f"New contact message #{contact_id}\n\n"
        f"From: {record['name']} <{record['email']}>\n"
        f"Subject: {record['subject']}\n\n"
        f"{record['message']}\n"
    )
    send_notification(f"TemberaGo Contact: {record['subject']}", body)
    log.info("Contact saved: #%d (%s)", contact_id, record["email"])

    return jsonify({
        "ok": True,
        "message": "Message sent! Our team will reply shortly.",
        "id": contact_id,
    })


@app.route("/api/quick-quote", methods=["POST"])
def api_quick_quote():
    data = request.get_json(silent=True) or {}

    required = ["service", "origin", "destination", "travel_date"]
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": "Please complete all quick quote fields."}), 400

    record = {
        "service":     data["service"].strip(),
        "origin":      data["origin"].strip(),
        "destination": data["destination"].strip(),
        "travel_date": data["travel_date"].strip(),
        "created_at":  datetime.utcnow().isoformat(),
    }

    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO quick_quotes (service, origin, destination, travel_date, created_at) "
                "VALUES (:service, :origin, :destination, :travel_date, :created_at)",
                record,
            )
            quote_id = cur.lastrowid
    except sqlite3.Error as exc:
        log.error("DB error saving quick quote: %s", exc)
        return jsonify({"ok": False, "error": "Failed to save quote. Please try again."}), 500

    body = (
        f"Quick quote request #{quote_id}\n\n"
        f"Service: {record['service']}\n"
        f"From: {record['origin']}\n"
        f"To: {record['destination']}\n"
        f"Date: {record['travel_date']}\n"
    )
    send_notification(f"TemberaGo Quick Quote #{quote_id}", body)
    log.info("Quick quote saved: #%d", quote_id)

    return jsonify({
        "ok": True,
        "message": "Quote request received! Scroll down to complete your details.",
        "id": quote_id,
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "TemberaGo"})


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

init_db()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
