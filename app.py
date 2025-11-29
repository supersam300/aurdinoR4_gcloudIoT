from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import base64
import json
import os

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///parking.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------------
# DATABASE MODEL
# -------------------------------
class SlotReading(db.Model):
    __tablename__ = "slot_readings"

    id = db.Column(db.Integer, primary_key=True)
    thing_id = db.Column(db.String(64))
    slot_id = db.Column(db.String(32))
    distance_cm = db.Column(db.Float)
    status = db.Column(db.String(32))
    device_timestamp_ms = db.Column(db.BigInteger)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SlotReading {self.slot_id} {self.status} {self.distance_cm}>"

with app.app_context():
    db.create_all()

# -------------------------------
# DASHBOARD PAGE
# -------------------------------
@app.route("/", methods=["GET"])
def index():
    latest_by_slot = {}
    for r in SlotReading.query.order_by(SlotReading.created_at.desc()).all():
        if r.slot_id not in latest_by_slot:
            latest_by_slot[r.slot_id] = r

    latest_slots = sorted(latest_by_slot.values(), key=lambda x: x.slot_id)
    recent_readings = SlotReading.query.order_by(SlotReading.created_at.desc()).limit(50).all()

    return render_template("index.html", latest_slots=latest_slots, recent_readings=recent_readings)

# -------------------------------
# ARDUINO + GOOGLE CLOUD RUN ENDPOINT (BASE64 ENVELOPE)
# -------------------------------
@app.route("/arduino-webhook", methods=["POST"])
def arduino_webhook():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "invalid_payload"}), 400

    try:
        outer_msg = data["message"]

        # Get Base64 string
        encoded = outer_msg.get("data", "")
        if not encoded:
            return jsonify({"error": "no data field"}), 400

        # Fix missing base64 padding
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += "=" * (4 - missing_padding)

        # Decode base64 → JSON dict
        decoded_json = json.loads(base64.b64decode(encoded).decode("utf-8"))

        # Extract the real message
        inner_msg = decoded_json.get("message", {})

        # Extract attributes → thing_id
        attributes = (
            inner_msg.get("attributes", {}) or
            outer_msg.get("attributes", {})
        )
        thing_id = attributes.get("thing_id", "unknown-parking-lot")

        # Timestamp
        timestamp_str = inner_msg.get("timestamp")
        try:
            device_ts = int(timestamp_str) if timestamp_str else None
        except:
            device_ts = None

        # Extract slots list
        slots = inner_msg.get("slots", [])
        if not isinstance(slots, list):
            slots = []

        # Save entries in DB
        saved_count = 0
        for slot in slots:
            new_reading = SlotReading(
                thing_id=thing_id,
                slot_id=slot.get("slot_id"),
                distance_cm=slot.get("distance_cm"),
                status=slot.get("status"),
                device_timestamp_ms=device_ts,
            )
            db.session.add(new_reading)
            saved_count += 1

        db.session.commit()
        return jsonify({"success": True, "saved": saved_count})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "processing_failed", "details": str(e)}), 500

# -------------------------------
# LIVE API (AJAX FETCHES THIS)
# -------------------------------
@app.route("/api/latest")
def api_latest():
    latest_by_slot = {}
    for r in SlotReading.query.order_by(SlotReading.created_at.desc()).all():
        if r.slot_id not in latest_by_slot:
            latest_by_slot[r.slot_id] = r

    latest_slots = sorted(latest_by_slot.values(), key=lambda x: x.slot_id)

    return jsonify([
        {
            "slot_id": r.slot_id,
            "status": r.status,
            "distance_cm": r.distance_cm,
            "thing_id": r.thing_id,
            "device_timestamp_ms": r.device_timestamp_ms,
            "created_at": r.created_at.isoformat()
        }
        for r in latest_slots
    ])

# -------------------------------
# TEST ENDPOINT (manual POST)
# -------------------------------
@app.route("/test-json", methods=["POST"])
def test_json():
    data = request.get_json()

    try:
        thing_id = data.get("thing_id", "parking-lot-1")
        slots = data.get("slots", [])

        saved_count = 0
        for slot in slots:
            reading = SlotReading(
                thing_id=thing_id,
                slot_id=slot.get("slot_id"),
                distance_cm=slot.get("distance_cm"),
                status=slot.get("status")
            )
            db.session.add(reading)
            saved_count += 1

        db.session.commit()
        return jsonify({"success": True, "saved": saved_count})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
