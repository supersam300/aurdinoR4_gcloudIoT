import os
import requests
import json
from flask import Flask, request

import logging
import google.cloud.logging

client = google.cloud.logging.Client()
client.setup_logging()

app = Flask(_name_)

DESTINATION_URL = "https://precious-unsparing-maple.ngrok-free.dev/arduino-webhook"
FORWARDING_SECRET = "e8a3b2f0-9c1d-4e5f-8a7b-6c5d4e3f2a1b"

@app.route("/", methods=["POST"])
def forward_webhook():
    envelope = request.get_json()
    if not envelope or "message" not in envelope:
        logging.error("Bad request: missing 'message'")
        return ("Bad Request", 400)

    try:
        # Forward EXACTLY what Arduino sent.
        forward_payload = envelope

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {FORWARDING_SECRET}"
        }

        response = requests.post(
            DESTINATION_URL,
            json=forward_payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        logging.info("Forward successful")
        return ("OK", 200)

    except Exception as e:
        logging.error(f"Forwarding error: {e}")
        return ("Forwarder Error", 500)

if _name_ == "_main_":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
