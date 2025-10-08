import os
import base64
import json
import requests
from flask import Flask, request

# <<< CHANGED: Import logging libraries
import logging
import google.cloud.logging

# <<< CHANGED: Set up Google Cloud Structured Logging
# This connects your logs to the Cloud Logging service
client = google.cloud.logging.Client()
client.setup_logging()

app = Flask(__name__)

DESTINATION_URL = " https://estrella-sapropelic-superinfinitely.ngrok-free.dev/arduino-webhook"
FORWARDING_SECRET = "e8a3b2f0-9c1d-4e5f-8a7b-6c5d4e3f2a1b" 

@app.route("/", methods=["POST"])
def forward_webhook():
    """
    Receives a push message from Pub/Sub, decodes it, and forwards it.
    """
    # Check if the destination URL was configured
    if not DESTINATION_URL:
        logging.error("FATAL: DESTINATION_URL environment variable is not set.")
        return ("Server Configuration Error", 500)

    envelope = request.get_json()
    if not envelope or "message" not in envelope:
        logging.warning("Received a bad request: Invalid Pub/Sub message format")
        return ("Bad Request: Invalid Pub/Sub message format", 400)

    try:
        message_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logging.info(f"Received raw data: {message_data}")
        
        payload = json.loads(message_data)

        
        headers = {'Content-Type': 'application/json'}
   
        if FORWARDING_SECRET:
            headers['Authorization'] = f"Bearer {FORWARDING_SECRET}"

     
        response = requests.post(DESTINATION_URL, data=json.dumps(payload), headers=headers, timeout=10)
        response.raise_for_status() 

        logging.info(f"Successfully forwarded data to {DESTINATION_URL}. Status: {response.status_code}")
        return ("OK", 200)

    except json.JSONDecodeError as e:
        logging.error(f"Could not decode JSON from Pub/Sub message: {e}")
        return ("Bad Request: Malformed data", 400)
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to forward webhook: {e}")
        return ("Server Error: Could not reach destination", 502) 
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return ("Server Error", 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))