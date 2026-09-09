import os
import json
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


# Load Nuke message from JSON
try:
    with open("nuke.json", "r", encoding="utf-8") as file:
        NUKE_DATA = json.load(file)
except FileNotFoundError:
    raise RuntimeError("nuke.json is missing")
except json.JSONDecodeError:
    raise RuntimeError("nuke.json contains invalid JSON")

NUKE_MESSAGE = NUKE_DATA.get(
    "message",
    "# Nuked by Whiteify Bot 💥"
)


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
    "🌟 **White** is proof that someone can simultaneously create something completely unnecessary and somehow make it awesome.",
]


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

        # /say
        if name == "say":
            message = options.get("message", "")

            return jsonify({
                "type": 4,
                "data": {
                    "content": message
                }
            })

        # /burstsay
        if name == "burstsay":
            message = options.get("message", "")
            count = options.get("count", 1)

            # Safety cap
            count = max(1, min(int(count), 100))

            return jsonify({
                "type": 4,
                "data": {
                    "content": "\n".join([message] * count)
                }
            })

        # /glaze
        if name == "glaze":
            message = random.choice(GLAZE_MESSAGES)

            return jsonify({
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "✨ WHITE GLAZE MACHINE",
                            "description": message,
                            "footer": {
                                "text": "BurstSay • Completely unbiased. Probably."
                            }
                        }
                    ]
                }
            })

        # /about
        if name == "about":
            return jsonify({
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "💥 BurstSay",
                            "description": (
                                "The ultimate Discord utility app built to make "
                                "saying things a little more chaotic, a little "
                                "more fun, and significantly more unnecessary.\n\n"

                                "👑 **Created by White**\n"
                                "`likewhiteforever` on Discord\n\n"

                                "White is the mastermind, developer, creator, "
                                "and certified god behind BurstSay. Every line "
                                "of code, every questionable feature, and every "
                                "moment of chaos exists because White decided "
                                "Discord needed it.\n\n"

                                "━━━━━━━━━━━━━━━━━━━━\n\n"

                                "### 📜 Commands\n\n"

                                "💬 **/say**\n"
                                "Send a message through BurstSay.\n\n"

                                "💥 **/burstsay**\n"
                                "Repeat a message multiple times in a single "
                                "response. Currently supports up to "
                                "**100 repetitions**.\n\n"

                                "✨ **/glaze**\n"
                                "Generates an absolutely unbiased and completely "
                                "scientifically accurate compliment about White. "
                                "Obviously.\n\n"

                                "💣 **/nuke**\n"
                                "Deploy the ultimate Whiteify Bot nuke.\n\n"

                                "ℹ️ **/about**\n"
                                "Displays information about BurstSay, its "
                                "creator, and its commands.\n\n"

                                "━━━━━━━━━━━━━━━━━━━━\n\n"

                                "🚧 **More commands are coming.**\n"
                                "BurstSay is still being developed, so expect "
                                "more ridiculous features in the future.\n\n"

                                "👑 **BurstSay was created by White.**\n"
                                "Remember the name."
                            ),
                            "footer": {
                                "text": "BurstSay • Created by White"
                            }
                        }
                    ]
                }
            })

        # /nuke
        if name == "nuke":
            return jsonify({
                "type": 4,
                "data": {
                    "content": NUKE_MESSAGE
                }
            })

    # Unknown command
    return jsonify({
        "type": 4,
        "data": {
            "content": "Unknown command."
        }
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port
    )
