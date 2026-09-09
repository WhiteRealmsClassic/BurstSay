import os
from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")

if not PUBLIC_KEY:
    raise RuntimeError("DISCORD_PUBLIC_KEY is missing from .env")

verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))


@app.before_request
def verify_discord_request():
    if request.path != "/interactions":
        return

    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")

    if not signature or not timestamp:
        return jsonify({"error": "Missing signature"}), 401

    body = request.get_data()

    try:
        verify_key.verify(
            timestamp.encode() + body,
            bytes.fromhex(signature)
        )
    except Exception:
        return jsonify({"error": "Invalid request signature"}), 401


@app.get("/")
def home():
    return "BurstSay is online"


@app.post("/interactions")
def interactions():
    data = request.get_json()

    # Discord Ping verification
    if data.get("type") == 1:
        return jsonify({"type": 1})

    # Slash command
    if data.get("type") == 2:
        command = data.get("data", {})
        name = command.get("name")

        options = {
            option["name"]: option.get("value")
            for option in command.get("options", [])
        }

        if name == "say":
            message = options.get("message", "")

            return jsonify({
                "type": 4,
                "data": {
                    "content": message
                }
            })

        if name == "burstsay":
            message = options.get("message", "")
            count = options.get("count", 1)

            # Safety cap
            count = max(1, min(int(count), 100))

            # We cannot make one interaction response produce
            # multiple Discord messages. For now, return a single
            # response showing the requested burst.
            return jsonify({
                "type": 4,
                "data": {
                    "content": "\n".join([message] * count)
                }
            })

    return jsonify({
        "type": 4,
        "data": {
            "content": "Unknown command."
        }
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
