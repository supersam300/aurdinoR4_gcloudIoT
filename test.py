from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():

    if request.is_json:
        data = request.get_json()
        print(" Authorized data received from Webhook:")
        print(f"   Alert: {data.get('alert')}")
        print(f"   Angle: {data.get('angle')}")
        print(f"   Distance: {data.get('distance_cm')} cm")

        return jsonify({"status": "success", "message": "Data received"}), 200
    else:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)