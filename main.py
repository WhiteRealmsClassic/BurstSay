import os
import json
import random
import time
import threading

import requests

from flask import Flask, request, jsonify

from nacl.signing import VerifyKey

from dotenv import load_dotenv

import chess

from chess_game import (
    get_game,
    create_game,
    delete_game,
    render_board,
    square_name,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# DISCORD PUBLIC KEY
# ============================================================

PUBLIC_KEY = os.getenv(
    "DISCORD_PUBLIC_KEY"
)


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
# DISCORD REQUEST VERIFICATION
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
# USER ID HELPER
# ============================================================

def get_user_id(data):

    # --------------------------------------------------------
    # Server / guild interaction
    # --------------------------------------------------------

    member = data.get(
        "member"
    )


    if isinstance(member, dict):

        user = member.get(
            "user"
        )


        if isinstance(user, dict):

            user_id = user.get(
                "id"
            )


            if user_id:

                return str(user_id)


    # --------------------------------------------------------
    # DM / GDM interaction
    # --------------------------------------------------------

    user = data.get(
        "user"
    )


    if isinstance(user, dict):

        user_id = user.get(
            "id"
        )


        if user_id:

            return str(user_id)


    return None


# ============================================================
# DELAYED NUKE
# ============================================================

def send_delayed_nuke(
    application_id,
    interaction_token,
    count
):

    webhook_url = (

        f"https://discord.com/api/v10/webhooks/"

        f"{application_id}/"
        f"{interaction_token}"

    )


    for _ in range(count):

        try:

            requests.post(

                webhook_url,

                json={
                    "content": NUKE_MESSAGE
                },

                timeout=15

            )

        except Exception:

            pass


        time.sleep(2)


# ============================================================
# CHESS WEBHOOK URL
# ============================================================

def get_original_message_url(
    application_id,
    interaction_token
):

    return (

        f"https://discord.com/api/v10/webhooks/"

        f"{application_id}/"
        f"{interaction_token}"

        "/messages/@original"

    )


# ============================================================
# SEND / UPDATE CHESS BOARD
# ============================================================

def send_chess_board(
    application_id,
    interaction_token,
    game,
    content
):

    webhook_url = get_original_message_url(

        application_id,

        interaction_token

    )


    image = render_board(
        game
    )


    payload = {

        "content": content,

        "embeds": [

            {

                "title": "♟️ BurstSay Chess",

                "description": (

                    f"**You:** "
                    f"{game.player_color_name}\n"

                    f"**BurstSay:** "
                    f"{game.bot_color_name}\n\n"

                    f"**Moves:** "
                    f"{len(game.move_history)}"

                ),

                "image": {

                    "url": "attachment://chess.png"

                },

                "footer": {

                    "text": (
                        "BurstSay Chess • "
                        "Play responsibly, "
                        "it's only chess."
                    )

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


    files = {

        "files[0]": (

            "chess.png",

            image,

            "image/png"

        )

    }


    form_data = {

        "payload_json": json.dumps(
            payload
        )

    }


    try:

        response = requests.patch(

            webhook_url,

            data=form_data,

            files=files,

            timeout=30

        )


        if not response.ok:

            print(
                "Chess board update failed:",
                response.status_code,
                response.text
            )

        else:

            print(
                "Chess board updated:",
                response.status_code
            )


    except Exception as error:

        print(
            "Chess board update exception:",
            repr(error)
        )


# ============================================================
# CHESS COMPONENTS
# ============================================================

def build_chess_components(game):

    components = []


    # ========================================================
    # GAME OVER
    # ========================================================

    if game.finished:

        components.append({

            "type": 1,

            "components": [

                {

                    "type": 2,

                    "style": 2,

                    "label": "New Game",

                    "custom_id": "chess_new"

                }

            ]

        })

        return components


    # ========================================================
    # SOURCE PIECES
    # ========================================================

    source_options = []


    if game.player_turn():

        for square in chess.SQUARES:

            piece = game.board.piece_at(
                square
            )


            if not piece:
                continue


            if piece.color != game.player_color:
                continue


            legal = game.legal_destinations(
                square
            )


            if not legal:
                continue


            source_options.append({

                "label": square_name(
                    square
                ),

                "value": str(
                    square
                ),

                "description": (

                    f"{piece.symbol()} • "

                    f"{len(legal)} "
                    f"legal move(s)"

                )

            })


    # --------------------------------------------------------
    # Source select
    # --------------------------------------------------------

    if source_options:

        components.append({

            "type": 1,

            "components": [

                {

                    "type": 3,

                    "custom_id": (
                        "chess_source"
                    ),

                    "placeholder": (
                        "Select a piece"
                    ),

                    "options": (
                        source_options[:25]
                    ),

                    "disabled": (
                        not game.player_turn()
                    )

                }

            ]

        })


    # ========================================================
    # DESTINATIONS
    # ========================================================

    if game.selected_square is not None:

        destinations = (
            game.legal_destinations(
                game.selected_square
            )
        )


        destination_options = []


        for square in destinations:

            destination_options.append({

                "label": square_name(
                    square
                ),

                "value": str(
                    square
                ),

                "description": (
                    "Move here"
                )

            })


        # Discord select menus support a
        # maximum of 25 options.
        #
        # A queen can have more than 25
        # legal destinations in some positions.
        #
        # So split destinations across
        # multiple select menus.

        chunks = [

            destination_options[i:i + 25]

            for i in range(
                0,
                len(destination_options),
                25
            )

        ]


        for index, chunk in enumerate(
            chunks[:2]
        ):

            components.append({

                "type": 1,

                "components": [

                    {

                        "type": 3,

                        "custom_id": (
                            f"chess_destination_{index}"
                        ),

                        "placeholder": (
                            "Select destination"
                            if index == 0
                            else
                            "More destinations"
                        ),

                        "options": chunk,

                        "disabled": (
                            not game.player_turn()
                        )

                    }

                ]

            })


    # ========================================================
    # BUTTONS
    # ========================================================

    components.append({

        "type": 1,

        "components": [

            {

                "type": 2,

                "style": 4,

                "label": "Resign",

                "custom_id": (
                    "chess_resign"
                ),

                "disabled": game.finished

            },

            {

                "type": 2,

                "style": 2,

                "label": "New Game",

                "custom_id": (
                    "chess_new"
                )

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

            "Select one of your pieces, "
            "then select its destination."

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


    if not data:

        return jsonify({

            "type": 4,

            "data": {

                "content": (
                    "❌ Invalid interaction."
                )

            }

        })


    # ========================================================
    # DISCORD PING
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

            option["name"]:
            option.get("value")

            for option in command.get(
                "options",
                []
            )

        }


        user_id = get_user_id(
            data
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

                min(
                    int(count),
                    100
                )

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

                            "title":
                            "✨ WHITE GLAZE MACHINE",

                            "description":
                            random.choice(
                                GLAZE_MESSAGES
                            ),

                            "footer": {

                                "text": (
                                    "BurstSay • "
                                    "Completely unbiased. "
                                    "Probably."
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

            if not user_id:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content": (
                            "❌ Could not identify "
                            "the player."
                        ),

                        "flags": 64

                    }

                })


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


            if color in (
                "random",
                None
            ):

                color = random.choice(
                    [
                        "white",
                        "black"
                    ]
                )


            # ------------------------------------------------
            # Remove previous game
            # ------------------------------------------------

            delete_game(
                user_id
            )


            # ------------------------------------------------
            # Create game
            # ------------------------------------------------

            game = create_game(

                user_id,

                color

            )


            # ------------------------------------------------
            # If player is Black,
            # BurstSay makes the first move.
            # ------------------------------------------------

            if (
                game.player_color
                == chess.BLACK
            ):

                game.make_bot_move()


            application_id = data.get(
                "application_id"
            )


            interaction_token = data.get(
                "token"
            )


            # ------------------------------------------------
            # Send board AFTER immediately
            # acknowledging Discord.
            #
            # This is the important fix.
            # ------------------------------------------------

            threading.Thread(

                target=send_chess_board,

                args=(

                    application_id,

                    interaction_token,

                    game,

                    chess_content(
                        game
                    )

                ),

                daemon=True

            ).start()


            # ------------------------------------------------
            # DEFERRED CHANNEL MESSAGE
            # ------------------------------------------------

            return jsonify({

                "type": 5

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

                                "The ultimate Discord "
                                "utility app built to make "
                                "saying things a little "
                                "more chaotic, a little "
                                "more fun, and significantly "
                                "more unnecessary.\n\n"

                                "👑 **Created by White**\n"
                                "`likewhiteforever` on Discord\n\n"

                                "━━━━━━━━━━━━━━━━━━━━\n\n"

                                "### 📜 Commands\n\n"

                                "💬 **/say**\n"
                                "Send a message through BurstSay.\n\n"

                                "💥 **/burstsay**\n"
                                "Repeat a message multiple times.\n\n"

                                "✨ **/glaze**\n"
                                "Generates an absolutely "
                                "unbiased compliment about White.\n\n"

                                "♟️ **/chess**\n"
                                "Play chess against BurstSay.\n\n"

                                "💣 **/nuke**\n"
                                "Repeat the nuke message "
                                "with a delay between messages.\n\n"

                                "ℹ️ **/about**\n"
                                "Displays information about BurstSay.\n\n"

                                "━━━━━━━━━━━━━━━━━━━━\n\n"

                                "🚧 **More commands are coming.**"

                            ),

                            "footer": {

                                "text":
                                "BurstSay • Created by White"

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

                min(
                    int(count),
                    20
                )

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

        custom_id = (

            data.get(
                "data",
                {}
            ).get(
                "custom_id"
            )

        )


        user_id = get_user_id(
            data
        )


        if not user_id:

            return jsonify({

                "type": 4,

                "data": {

                    "content":
                    "❌ Could not identify the player.",

                    "flags": 64

                }

            })


        game = get_game(
            user_id
        )


        if not game:

            return jsonify({

                "type": 4,

                "data": {

                    "content":
                    "❌ You don't have an active chess game.",

                    "flags": 64

                }

            })


        application_id = data.get(
            "application_id"
        )


        interaction_token = data.get(
            "token"
        )


        # ====================================================
        # SOURCE SELECT
        # ====================================================

        if custom_id == "chess_source":

            if not game.player_turn():

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "⏳ It's BurstSay's turn.",

                        "flags": 64

                    }

                })


            values = (

                data.get(
                    "data",
                    {}
                ).get(
                    "values",
                    []
                )

            )


            if not values:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "Select a piece first.",

                        "flags": 64

                    }

                })


            try:

                square = int(
                    values[0]
                )

            except ValueError:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "❌ Invalid square.",

                        "flags": 64

                    }

                })


            piece = game.board.piece_at(
                square
            )


            if not piece:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "There isn't a piece there.",

                        "flags": 64

                    }

                })


            if piece.color != game.player_color:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "That's not your piece.",

                        "flags": 64

                    }

                })


            legal = game.legal_destinations(
                square
            )


            if not legal:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "That piece has no legal moves.",

                        "flags": 64

                    }

                })


            game.selected_square = square


            # ------------------------------------------------
            # Acknowledge the component immediately.
            # ------------------------------------------------

            threading.Thread(

                target=send_chess_board,

                args=(

                    application_id,

                    interaction_token,

                    game,

                    (
                        f"♟️ **{square_name(square)} "
                        "selected.**\n"
                        "Now select your destination."
                    )

                ),

                daemon=True

            ).start()


            # ------------------------------------------------
            # DEFERRED UPDATE MESSAGE
            # ------------------------------------------------

            return jsonify({

                "type": 6

            })


        # ====================================================
        # DESTINATION SELECT
        # ====================================================

        if custom_id.startswith(
            "chess_destination"
        ):

            if not game.player_turn():

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "⏳ It's BurstSay's turn.",

                        "flags": 64

                    }

                })


            values = (

                data.get(
                    "data",
                    {}
                ).get(
                    "values",
                    []
                )

            )


            if not values:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "Select a destination.",

                        "flags": 64

                    }

                })


            if game.selected_square is None:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "Select a piece first.",

                        "flags": 64

                    }

                })


            try:

                to_square = int(
                    values[0]
                )

            except ValueError:

                return jsonify({

                    "type": 4,

                    "data": {

                        "content":
                        "❌ Invalid destination.",

                        "flags": 64

                    }

                })


            from_square = (
                game.selected_square
            )


            # ------------------------------------------------
            # Player move
            # ------------------------------------------------

            success, result = (
                game.make_player_move(

                    from_square,

                    to_square

                )
            )


            game.selected_square = None


            if not success:

                threading.Thread(

                    target=send_chess_board,

                    args=(

                        application_id,

                        interaction_token,

                        game,

                        f"❌ {result}"

                    ),

                    daemon=True

                ).start()


                return jsonify({

                    "type": 6

                })


            # ------------------------------------------------
            # Player checkmate / draw
            # ------------------------------------------------

            if game.finished:

                threading.Thread(

                    target=send_chess_board,

                    args=(

                        application_id,

                        interaction_token,

                        game,

                        chess_content(
                            game
                        )

                    ),

                    daemon=True

                ).start()


                return jsonify({

                    "type": 6

                })


            # ------------------------------------------------
            # Bot move
            # ------------------------------------------------

            bot_move = game.make_bot_move()


            if game.finished:

                content = chess_content(
                    game
                )

            else:

                content = (

                    f"♟️ **You played `{result}`**\n\n"

                    f"🤖 **BurstSay played "
                    f"`{bot_move}`**\n\n"

                    f"{chess_content(game)}"

                )


            threading.Thread(

                target=send_chess_board,

                args=(

                    application_id,

                    interaction_token,

                    game,

                    content

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 6

            })


        # ====================================================
        # RESIGN
        # ====================================================

        if custom_id == "chess_resign":

            game.resign()


            threading.Thread(

                target=send_chess_board,

                args=(

                    application_id,

                    interaction_token,

                    game,

                    (
                        "🏳️ **You resigned.**\n\n"
                        "BurstSay wins."
                    )

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 6

            })


        # ====================================================
        # NEW GAME
        # ====================================================

        if custom_id == "chess_new":

            delete_game(
                user_id
            )


            color = random.choice(
                [
                    "white",
                    "black"
                ]
            )


            game = create_game(

                user_id,

                color

            )


            if (
                game.player_color
                == chess.BLACK
            ):

                game.make_bot_move()


            threading.Thread(

                target=send_chess_board,

                args=(

                    application_id,

                    interaction_token,

                    game,

                    chess_content(
                        game
                    )

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 6

            })


    # ========================================================
    # UNKNOWN
    # ========================================================

    return jsonify({

        "type": 4,

        "data": {

            "content":
            "Unknown command."

        }

    })


# ============================================================
# START SERVER
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
