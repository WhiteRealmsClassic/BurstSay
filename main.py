import os
import json
import random
import time
import threading

import requests

from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from dotenv import load_dotenv

from chess_game import (
    get_game,
    create_game,
    delete_game,
    render_board,
    square_name,
)

import chess


load_dotenv()

app = Flask(__name__)


# ============================================================
# DISCORD
# ============================================================

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")

if not PUBLIC_KEY:
    raise RuntimeError(
        "DISCORD_PUBLIC_KEY is missing from .env"
    )

verify_key = VerifyKey(
    bytes.fromhex(PUBLIC_KEY)
)


# ============================================================
# NUKE MESSAGE
# ============================================================

try:

    with open(
        "nuke.json",
        "r",
        encoding="utf-8"
    ) as file:

        NUKE_DATA = json.load(file)

except FileNotFoundError:

    raise RuntimeError(
        "nuke.json is missing"
    )

except json.JSONDecodeError:

    raise RuntimeError(
        "nuke.json contains invalid JSON"
    )


NUKE_MESSAGE = NUKE_DATA.get(
    "message",
    "# Nuked by Whiteify Bot 💥"
)


# ============================================================
# GLAZE
# ============================================================

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


# ============================================================
# CHESS TRASH TALK
# ============================================================

CHESS_MESSAGES = {

    "player_move": [
        "Interesting move. Humanity continues to surprise me.",
        "I'll allow it. For now. ♟️",
        "Not terrible. Suspiciously competent.",
        "You actually know how chess works. Concerning.",
        "That move has been accepted by the council of pixels.",
    ],

    "bot_move": [
        "Your turn. Try not to embarrass yourself.",
        "♟️ Your move, grandmaster.",
        "I have moved a piece. This is becoming serious.",
        "Your move. The board awaits your questionable decision.",
        "Think carefully. I have absolutely no mercy.",
    ],

    "win": [
        "CHECKMATE. 🗿",
        "Game over. The board has spoken.",
        "You lost to BurstSay. This information will be remembered.",
        "♟️ Checkmate. Humanity has fallen once again.",
    ],

    "loss": [
        "You actually beat me. I am choosing to blame the hardware.",
        "CHECKMATE. Fine. You win. 😭",
        "You won. This is deeply inconvenient.",
        "Apparently you can play chess. Respect.",
    ],

    "draw": [
        "Draw. Neither of us gets bragging rights.",
        "The board refuses to choose a winner.",
        "♟️ Stalemate. Humanity survives another day.",
    ],
}


# ============================================================
# VERIFY DISCORD REQUEST
# ============================================================

@app.before_request
def verify_discord_request():

    if request.path != "/interactions":
        return

    signature = request.headers.get(
        "X-Signature-Ed25519"
    )

    timestamp = request.headers.get(
        "X-Signature-Timestamp"
    )

    if not signature or not timestamp:

        return jsonify({
            "error": "Missing signature"
        }), 401

    body = request.get_data()

    try:

        verify_key.verify(
            timestamp.encode() + body,
            bytes.fromhex(signature)
        )

    except Exception:

        return jsonify({
            "error": "Invalid request signature"
        }), 401


# ============================================================
# NUKE SENDER
# ============================================================

def send_delayed_nuke(
    application_id,
    interaction_token,
    count
):

    webhook_url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{application_id}/{interaction_token}"
    )

    for _ in range(count):

        try:

            requests.post(
                webhook_url,
                json={
                    "content": NUKE_MESSAGE
                }
            )

        except Exception:
            pass

        time.sleep(2)


# ============================================================
# CHESS IMAGE UPLOAD
# ============================================================

def send_chess_board(
    application_id,
    interaction_token,
    game,
    content
):

    webhook_url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{application_id}/{interaction_token}"
        "/messages/@original"
    )

    image = render_board(game)

    files = {
        "files[0]": (
            "chess.png",
            image,
            "image/png"
        )
    }

    payload = {
        "payload_json": json.dumps({
            "content": content,
            "embeds": [
                {
                    "title": "♟️ BurstSay Chess",
                    "description": (
                        f"**You:** {game.player_color_name}\n"
                        f"**BurstSay:** {game.bot_color_name}\n\n"
                        f"**Moves:** {len(game.move_history)}"
                    ),
                    "image": {
                        "url": "attachment://chess.png"
                    },
                    "footer": {
                        "text": "BurstSay Chess"
                    }
                }
            ],
            "components": build_chess_components(game)
        })
    }

    try:

        requests.patch(
            webhook_url,
            data=payload,
            files=files
        )

    except Exception:
        pass


# ============================================================
# CHESS COMPONENTS
# ============================================================

def build_chess_components(game):

    components = []

    # --------------------------------------------------------
    # Source square
    # --------------------------------------------------------

    source_options = []

    for square in chess.SQUARES:

        piece = game.board.piece_at(square)

        if not piece:
            continue

        if piece.color != game.player_color:
            continue

        legal = game.legal_destinations(square)

        if not legal:
            continue

        source_options.append({
            "label": square_name(square),
            "value": str(square),
            "description": (
                f"{piece.symbol()} "
                f"{len(legal)} legal move(s)"
            )
        })

    if source_options:

        components.append({
            "type": 1,
            "components": [
                {
                    "type": 3,
                    "custom_id": "chess_source",
                    "placeholder": "Select a piece",
                    "options": source_options[:25],
                    "disabled": (
                        game.finished
                        or not game.player_turn()
                    )
                }
            ]
        })

    # --------------------------------------------------------
    # Destination
    # --------------------------------------------------------

    if game.selected_square is not None:

        destinations = game.legal_destinations(
            game.selected_square
        )

        destination_options = []

        for square in destinations:

            destination_options.append({
                "label": square_name(square),
                "value": str(square),
                "description": "Make this move"
            })

        if destination_options:

            components.append({
                "type": 1,
                "components": [
                    {
                        "type": 3,
                        "custom_id": "chess_destination",
                        "placeholder": "Select destination",
                        "options": destination_options[:25],
                        "disabled": (
                            game.finished
                            or not game.player_turn()
                        )
                    }
                ]
            })

    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    components.append({
        "type": 1,
        "components": [

            {
                "type": 2,
                "style": 4,
                "label": "Resign",
                "custom_id": "chess_resign",
                "disabled": game.finished
            },

            {
                "type": 2,
                "style": 2,
                "label": "New Game",
                "custom_id": "chess_new",
            }

        ]
    })

    return components


# ============================================================
# CHESS CONTENT
# ============================================================

def chess_content(game):

    if game.finished:

        if game.result == "win":
            return random.choice(
                CHESS_MESSAGES["win"]
            )

        if game.result == "loss":
            return random.choice(
                CHESS_MESSAGES["loss"]
            )

        return random.choice(
            CHESS_MESSAGES["draw"]
        )

    if game.player_turn():

        return (
            "♟️ **Your turn.**\n"
            "Select one of your pieces, then select its destination."
        )

    return random.choice(
        CHESS_MESSAGES["bot_move"]
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return "BurstSay is online"


# ============================================================
# INTERACTIONS
# ============================================================

@app.post("/interactions")
def interactions():

    data = request.get_json()

    # ========================================================
    # PING
    # ========================================================

    if data.get("type") == 1:

        return jsonify({
            "type": 1
        })

    # ========================================================
    # SLASH COMMAND
    # ========================================================

    if data.get("type") == 2:

        command = data.get(
            "data",
            {}
        )

        name = command.get(
            "name"
        )

        options = {
            option["name"]: option.get("value")
            for option in command.get(
                "options",
                []
            )
        }

        user = data.get(
            "member",
            {}
        ).get(
            "user",
            {}
        )

        user_id = user.get(
            "id"
        )

        # ====================================================
        # /say
        # ====================================================

        if name == "say":

            message = options.get(
                "message",
                ""
            )

            return jsonify({
                "type": 4,
                "data": {
                    "content": message
                }
            })

        # ====================================================
        # /burstsay
        # ====================================================

        if name == "burstsay":

            message = options.get(
                "message",
                ""
            )

            count = options.get(
                "count",
                1
            )

            count = max(
                1,
                min(int(count), 100)
            )

            return jsonify({
                "type": 4,
                "data": {
                    "content": "\n".join(
                        [message] * count
                    )
                }
            })

        # ====================================================
        # /glaze
        # ====================================================

        if name == "glaze":

            return jsonify({
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "✨ WHITE GLAZE MACHINE",
                            "description": random.choice(
                                GLAZE_MESSAGES
                            ),
                            "footer": {
                                "text": (
                                    "BurstSay • Completely unbiased. Probably."
                                )
                            }
                        }
                    ]
                }
            })

        # ====================================================
        # /chess
        # ====================================================

        if name == "chess":

            color = options.get(
                "color"
            )

            if color not in (
                "white",
                "black",
                "random",
                None
            ):
                color = "random"

            if color == "random":
                color = random.choice(
                    ["white", "black"]
                )

            # Kill old game
            delete_game(user_id)

            game = create_game(
                user_id,
                color
            )

            # ------------------------------------------------
            # If player is black, bot makes first move.
            # ------------------------------------------------

            if game.player_color == chess.BLACK:

                game.make_bot_move()

            image = render_board(game)

            return jsonify({
                "type": 4,
                "data": {
                    "content": chess_content(game),
                    "embeds": [
                        {
                            "title": "♟️ BurstSay Chess",
                            "description": (
                                f"**You:** {game.player_color_name}\n"
                                f"**BurstSay:** {game.bot_color_name}\n\n"
                                f"**Moves:** 0"
                            ),
                            "image": {
                                "url": "attachment://chess.png"
                            },
                            "footer": {
                                "text": "BurstSay Chess"
                            }
                        }
                    ],
                    "components": build_chess_components(
                        game
                    ),
                    "attachments": [
                        {
                            "id": "0",
                            "filename": "chess.png"
                        }
                    ]
                }
            })

        # ====================================================
        # /about
        # ====================================================

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

                                "━━━━━━━━━━━━━━━━━━━━\n\n"

                                "### 📜 Commands\n\n"

                                "💬 **/say**\n"
                                "Send a message through BurstSay.\n\n"

                                "💥 **/burstsay**\n"
                                "Repeat a message multiple times.\n\n"

                                "✨ **/glaze**\n"
                                "Generates an absolutely unbiased compliment "
                                "about White.\n\n"

                                "💣 **/nuke**\n"
                                "Repeat the nuke message, spaced 2 seconds apart.\n\n"

                                "♟️ **/chess**\n"
                                "Play a game of chess against BurstSay.\n\n"

                                "ℹ️ **/about**\n"
                                "Displays information about BurstSay.\n\n"

                                "━━━━━━━━━━━━━━━━━━━━\n\n"

                                "🚧 More commands are coming."
                            ),
                            "footer": {
                                "text": "BurstSay • Created by White"
                            }
                        }
                    ]
                }
            })

        # ====================================================
        # /nuke
        # ====================================================

        if name == "nuke":

            count = options.get(
                "count",
                1
            )

            count = max(
                1,
                min(int(count), 20)
            )

            application_id = data.get(
                "application_id"
            )

            interaction_token = data.get(
                "token"
            )

            threading.Thread(
                target=send_delayed_nuke,
                args=(
                    application_id,
                    interaction_token,
                    count
                ),
                daemon=True
            ).start()

            return jsonify({
                "type": 5
            })

    # ========================================================
    # COMPONENT INTERACTION
    # ========================================================

    if data.get("type") == 3:

        custom_id = data.get(
            "data",
            {}
        ).get(
            "custom_id"
        )

        user = data.get(
            "member",
            {}
        ).get(
            "user",
            {}
        )

        user_id = user.get(
            "id"
        )

        game = get_game(user_id)

        if not game:

            return jsonify({
                "type": 4,
                "data": {
                    "content": (
                        "❌ You don't have an active chess game."
                    ),
                    "flags": 64
                }
            })

        # ====================================================
        # SOURCE
        # ====================================================

        if custom_id == "chess_source":

            if not game.player_turn():

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "⏳ It's Burstsay's turn.",
                        "flags": 64
                    }
                })

            values = data.get(
                "data",
                {}
            ).get(
                "values",
                []
            )

            if not values:

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "Select a piece first.",
                        "flags": 64
                    }
                })

            square = int(
                values[0]
            )

            piece = game.board.piece_at(
                square
            )

            if not piece:
                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "There isn't a piece there.",
                        "flags": 64
                    }
                })

            if piece.color != game.player_color:

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "That's not your piece.",
                        "flags": 64
                    }
                })

            if not game.legal_destinations(
                square
            ):

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "That piece has no legal moves.",
                        "flags": 64
                    }
                })

            game.selected_square = square

            return jsonify({
                "type": 7,
                "data": {
                    "content": (
                        f"♟️ **{square_name(square)} selected.**\n"
                        "Now select where you want to move it."
                    ),
                    "components": build_chess_components(
                        game
                    )
                }
            })

        # ====================================================
        # DESTINATION
        # ====================================================

        if custom_id == "chess_destination":

            if not game.player_turn():

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "⏳ It's Burstsay's turn.",
                        "flags": 64
                    }
                })

            values = data.get(
                "data",
                {}
            ).get(
                "values",
                []
            )

            if not values:

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "Select a destination.",
                        "flags": 64
                    }
                })

            if game.selected_square is None:

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "Select a piece first.",
                        "flags": 64
                    }
                })

            from_square = game.selected_square
            to_square = int(
                values[0]
            )

            success, result = game.make_player_move(
                from_square,
                to_square
            )

            game.selected_square = None

            if not success:

                return jsonify({
                    "type": 4,
                    "data": {
                        "content": f"❌ {result}",
                        "flags": 64
                    }
                })

            # ------------------------------------------------
            # Player delivered checkmate
            # ------------------------------------------------

            if game.finished:

                return jsonify({
                    "type": 7,
                    "data": {
                        "content": chess_content(game),
                        "components": build_chess_components(
                            game
                        )
                    }
                })

            # ------------------------------------------------
            # Bot move
            # ------------------------------------------------

            bot_move = game.make_bot_move()

            if game.finished:

                return jsonify({
                    "type": 7,
                    "data": {
                        "content": chess_content(game),
                        "components": build_chess_components(
                            game
                        )
                    }
                })

            return jsonify({
                "type": 7,
                "data": {
                    "content": (
                        f"♟️ **You played `{result}`**\n\n"
                        f"🤖 **BurstSay played `{bot_move}`**\n\n"
                        f"{chess_content(game)}"
                    ),
                    "components": build_chess_components(
                        game
                    )
                }
            })

        # ====================================================
        # RESIGN
        # ====================================================

        if custom_id == "chess_resign":

            game.resign()

            return jsonify({
                "type": 7,
                "data": {
                    "content": (
                        "🏳️ **You resigned.**\n\n"
                        "BurstSay wins."
                    ),
                    "components": build_chess_components(
                        game
                    )
                }
            })

        # ====================================================
        # NEW GAME
        # ====================================================

        if custom_id == "chess_new":

            color = random.choice(
                ["white", "black"]
            )

            game = create_game(
                user_id,
                color
            )

            if game.player_color == chess.BLACK:

                game.make_bot_move()

            return jsonify({
                "type": 7,
                "data": {
                    "content": chess_content(game),
                    "components": build_chess_components(
                        game
                    )
                }
            })

    # ========================================================
    # UNKNOWN
    # ========================================================

    return jsonify({
        "type": 4,
        "data": {
            "content": "Unknown command."
        }
    })


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
