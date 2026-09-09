import os
import random

from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")

if not PUBLIC_KEY:
    raise RuntimeError("DISCORD_PUBLIC_KEY is missing from .env")

verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))


# --------------------------------------------------
# Discord request verification
# --------------------------------------------------

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


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.get("/")
def home():
    return "BurstSay is online"


# --------------------------------------------------
# Glaze messages
# --------------------------------------------------

GLAZE_MESSAGES = [
    "👑 **White** isn't just a developer. White is what happens when coding skill decides to become a person.",

    "🔥 **White** is genuinely built different. While everyone else is still reading the documentation, White has already shipped the feature.",

    "🚀 **White** has the kind of developer energy that makes bugs voluntarily fix themselves.",

    "🧠 **White** doesn't write code. White negotiates with computers until they agree to do exactly what was intended.",

    "⚡ If **White** starts coding, the rest of the developers might as well open spectator mode.",

    "👑 **White** aka `likewhiteforever` is officially too powerful. Discord should probably add a separate developer tier just for this person.",

    "💻 Every project becomes 10x more interesting when **White** touches it. Coincidence? Absolutely not.",

    "🏆 **White** has the rare ability to turn 'I have an idea' into an actual working project.",

    "🔥 `likewhiteforever` isn't just a Discord username. It's a warning to every bug in the codebase.",

    "🌟 **White** is proof that someone can simultaneously create something completely unnecessary and somehow make it awesome."
]


# --------------------------------------------------
# Discord interactions
# --------------------------------------------------

@app.post("/interactions")
def interactions():
    data = request.get_json()

    # Discord Ping verification
    if data.get("type") == 1:
        return jsonify({
            "type": 1
        })

    # Slash command
    if data.get("type") == 2:
        command = data.get("data", {})
        name = command.get("name")

        options = {
            option["name"]: option.get("value")
            for option in command.get("options", [])
        }

        # ------------------------------------------
        # /say
        # ------------------------------------------

        if name == "say":
            message = options.get("message", "")

            return jsonify({
                "type": 4,
                "data": {
                    "content": message
                }
            })

        # ------------------------------------------
        # /burstsay
        # ------------------------------------------

        if name == "burstsay":
            message = options.get("message", "")
            count = options.get("count", 1)

            # Hard safety cap
            count = max(1, min(int(count), 100))

            return jsonify({
                "type": 4,
                "data": {
                    "content": "\n".join([message] * count)
                }
            })

        # ------------------------------------------
        # /glaze
        # ------------------------------------------

        if name == "glaze":
            message = random.choice(GLAZE_MESSAGES)

            return jsonify({
                "type": 4,
                "data": {
                    "content": message
                }
            })

    # Unknown command
    return jsonify({
        "type": 4,
        "data": {
            "content": "Unknown command."
        }
    })


# --------------------------------------------------
# Run server
# --------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port
    )
