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
import akinator

from chess_game import (
    get_game,
    create_game,
    delete_game,
    render_board,
    square_name,
)


# ============================================================
# ENV
# ============================================================

load_dotenv()


PUBLIC_KEY = os.getenv(
    "DISCORD_PUBLIC_KEY"
)

BOT_TOKEN = os.getenv(
    "DISCORD_TOKEN"
)


if not PUBLIC_KEY:
    raise RuntimeError(
        "DISCORD_PUBLIC_KEY is missing from .env"
    )


if not BOT_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from .env"
    )


verify_key = VerifyKey(
    bytes.fromhex(
        PUBLIC_KEY
    )
)


app = Flask(__name__)


# ============================================================
# PENDING CHESS INVITES
# ============================================================

PENDING_INVITES = {}

PENDING_INVITES_LOCK = threading.Lock()


# ============================================================
# AKINATOR
# ============================================================

AKINATOR_GAMES = {}

AKINATOR_LOCK = threading.Lock()

AKINATOR_THEMES = {
    "character": "c",
    "animal": "a",
    "object": "o",
}

AKINATOR_THEME_NAMES = {
    "c": "Character",
    "a": "Animal",
    "o": "Object",
}


def get_akinator_game(user_id):

    with AKINATOR_LOCK:

        return AKINATOR_GAMES.get(
            str(user_id)
        )


def set_akinator_game(
    user_id,
    game
):

    with AKINATOR_LOCK:

        AKINATOR_GAMES[
            str(user_id)
        ] = game


def delete_akinator_game(
    user_id
):

    with AKINATOR_LOCK:

        AKINATOR_GAMES.pop(
            str(user_id),
            None
        )


def akinator_buttons(
    user_id
):

    uid = str(user_id)

    return [

        {
            "type": 1,

            "components": [

                {
                    "type": 2,

                    "style": 3,

                    "label":
                    "Yes",

                    "emoji": {
                        "name":
                        "✅"
                    },

                    "custom_id":
                    f"aki_answer:yes:{uid}"
                },

                {
                    "type": 2,

                    "style": 4,

                    "label":
                    "No",

                    "emoji": {
                        "name":
                        "❌"
                    },

                    "custom_id":
                    f"aki_answer:no:{uid}"
                },

                {
                    "type": 2,

                    "style": 2,

                    "label":
                    "Don't know",

                    "emoji": {
                        "name":
                        "❓"
                    },

                    "custom_id":
                    f"aki_answer:idk:{uid}"
                }

            ]
        },

        {
            "type": 1,

            "components": [

                {
                    "type": 2,

                    "style": 1,

                    "label":
                    "Probably",

                    "emoji": {
                        "name":
                        "🤔"
                    },

                    "custom_id":
                    f"aki_answer:probably:{uid}"
                },

                {
                    "type": 2,

                    "style": 2,

                    "label":
                    "Probably not",

                    "emoji": {
                        "name":
                        "🙅"
                    },

                    "custom_id":
                    f"aki_answer:probably_not:{uid}"
                }

            ]
        }

    ]


def akinator_question_data(
    game,
    user_id,
    theme_name,
    intro=False
):

    try:

        progression = float(
            getattr(
                game,
                "progression",
                0
            )
        )

    except Exception:

        progression = 0


    try:

        step = int(
            getattr(
                game,
                "step",
                0
            )
        ) + 1

    except Exception:

        step = 1


    if intro:

        content = (

            f"🧞 **BurstSay Akinator — "
            f"{theme_name}**\n\n"

            "Think of something and keep it secret.\n"
            "I'll try to figure it out.\n\n"

        )

    else:

        content = (

            f"🧞 **BurstSay Akinator — "
            f"{theme_name}**\n\n"

        )


    content += (

        f"**Question {step}**\n"

        f"> {game.question}\n\n"

        f"🧠 **Progress:** "
        f"{progression:.0f}%"

    )


    return {

        "content":
        content,

        "components":
        akinator_buttons(
            user_id
        )

    }


def akinator_guess_data(
    game,
    user_id
):

    name = (

        getattr(
            game,
            "name_proposition",
            None
        )

        or

        "something"

    )


    description = (

        getattr(
            game,
            "description_proposition",
            None
        )

        or

        "I don't have a description for this guess."

    )


    photo = (

        getattr(
            game,
            "photo",
            None
        )

        or

        None

    )


    embed = {

        "title":
        "🔮 I think I know it...",

        "description": (

            f"### {name}\n\n"

            f"{description}"

        ),

        "footer": {

            "text":
            "Was I right?"

        }

    }


    if photo:

        embed["thumbnail"] = {

            "url":
            photo

        }


    return {

        "content":
        "🧞 **My guess is...**",

        "embeds": [
            embed
        ],

        "components": [

            {

                "type": 1,

                "components": [

                    {

                        "type": 2,

                        "style": 3,

                        "label":
                        "Yes, you got it!",

                        "emoji": {
                            "name":
                            "✅"
                        },

                        "custom_id":
                        f"aki_guess:yes:{user_id}"

                    },

                    {

                        "type": 2,

                        "style": 4,

                        "label":
                        "No",

                        "emoji": {
                            "name":
                            "❌"
                        },

                        "custom_id":
                        f"aki_guess:no:{user_id}"

                    }

                ]

            }

        ]

    }


def start_akinator(
    user_id,
    theme
):

    game = akinator.Akinator()

    game.start_game(
        theme=theme
    )

    set_akinator_game(
        user_id,
        game
    )

    return game


# ============================================================
# NUKE
# ============================================================

try:

    with open(
        "nuke.json",
        "r",
        encoding="utf-8"
    ) as file:

        NUKE_DATA = json.load(
            file
        )

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
# DISCORD VERIFICATION
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

            "error":
            "Missing signature"

        }), 401


    body = request.get_data()


    try:

        verify_key.verify(

            timestamp.encode()
            + body,

            bytes.fromhex(
                signature
            )

        )

    except Exception:

        return jsonify({

            "error":
            "Invalid request signature"

        }), 401


# ============================================================
# USER ID
# ============================================================

def get_user_id(data):

    member = data.get(
        "member"
    )


    if isinstance(
        member,
        dict
    ):

        user = member.get(
            "user"
        )


        if isinstance(
            user,
            dict
        ):

            if user.get("id"):

                return str(
                    user["id"]
                )


    user = data.get(
        "user"
    )


    if isinstance(
        user,
        dict
    ):

        if user.get("id"):

            return str(
                user["id"]
            )


    return None


# ============================================================
# USER DISPLAY NAME
# ============================================================

def get_user_name(data):

    member = data.get(
        "member"
    )


    if isinstance(
        member,
        dict
    ):

        user = member.get(
            "user"
        )


        if isinstance(
            user,
            dict
        ):

            return (

                user.get(
                    "global_name"
                )

                or

                user.get(
                    "username"
                )

                or

                "Player"

            )


    user = data.get(
        "user"
    )


    if isinstance(
        user,
        dict
    ):

        return (

            user.get(
                "global_name"
            )

            or

            user.get(
                "username"
            )

            or

            "Player"

        )


    return "Player"


# ============================================================
# NUKE
# ============================================================

def send_delayed_nuke(

    application_id,

    interaction_token,

    count

):

    webhook_url = (

        "https://discord.com/api/v10/webhooks/"

        f"{application_id}/"
        f"{interaction_token}"

    )


    for _ in range(count):

        try:

            requests.post(

                webhook_url,

                json={
                    "content":
                    NUKE_MESSAGE
                },

                timeout=15

            )

        except Exception:

            pass


        time.sleep(2)


# ============================================================
# ORIGINAL MESSAGE URL
# ============================================================

def original_message_url(

    application_id,

    interaction_token

):

    return (

        "https://discord.com/api/v10/webhooks/"

        f"{application_id}/"
        f"{interaction_token}"

        "/messages/@original"

    )


# ============================================================
# CHESS CONTENT
# ============================================================

def chess_content(
    game,
    extra=None
):

    if extra:

        return extra


    if game.finished:

        if game.result == "draw":

            return (
                "🤝 **Draw.**\n"
                "Neither player gets bragging rights."
            )


        return (

            f"🏆 **{game.winner_name} wins!**\n"
            "Checkmate."

        )


    return (

        f"♟️ **{game.current_player_name}'s turn.**\n"

        "Select a piece, then select its destination."

    )


# ============================================================
# CHESS COMPONENTS
# ============================================================

def build_chess_components(
    game
):

    if game.finished:

        return [

            {

                "type": 1,

                "components": [

                    {

                        "type": 2,

                        "style": 2,

                        "label":
                        "New Game",

                        "custom_id":
                        "chess_new"

                    }

                ]

            }

        ]


    rows = []


    # ========================================================
    # PIECE SELECT
    # ========================================================

    source_options = []


    if game.current_player_id:

        for square in chess.SQUARES:

            piece = game.board.piece_at(
                square
            )


            if not piece:

                continue


            if piece.color != (
                game.board.turn
            ):

                continue


            legal = (
                game.legal_destinations(
                    square
                )
            )


            if not legal:

                continue


            source_options.append({

                "label":
                square_name(square),

                "value":
                str(square),

                "description": (

                    f"{piece.symbol()} • "
                    f"{len(legal)} legal move(s)"

                )

            })


    if source_options:

        rows.append({

            "type": 1,

            "components": [

                {

                    "type": 3,

                    "custom_id":
                    "chess_source",

                    "placeholder":
                    "Select a piece",

                    "options":
                    source_options[:25]

                }

            ]

        })


    # ========================================================
    # DESTINATION SELECT
    # ========================================================

    if game.selected_square is not None:

        destination_options = []


        for square in (
            game.legal_destinations(
                game.selected_square
            )
        ):

            destination_options.append({

                "label":
                square_name(square),

                "value":
                str(square),

                "description":
                "Move here"

            })


        for index in range(

            0,

            len(destination_options),

            25

        ):

            if len(rows) >= 4:

                break


            rows.append({

                "type": 1,

                "components": [

                    {

                        "type": 3,

                        "custom_id": (

                            "chess_destination_"

                            + str(
                                index // 25
                            )

                        ),

                        "placeholder":
                        "Select destination",

                        "options":
                        destination_options[
                            index:index + 25
                        ]

                    }

                ]

            })


    # ========================================================
    # CONTROLS
    # ========================================================

    if len(rows) < 5:

        rows.append({

            "type": 1,

            "components": [

                {

                    "type": 2,

                    "style": 4,

                    "label":
                    "Resign",

                    "custom_id":
                    "chess_resign"

                },

                {

                    "type": 2,

                    "style": 2,

                    "label":
                    "New Game",

                    "custom_id":
                    "chess_new"

                }

            ]

        })


    return rows


# ============================================================
# UPDATE CHESS MESSAGE
# ============================================================

def edit_chess_message(

    application_id,

    interaction_token,

    game,

    content

):

    webhook_url = original_message_url(

        application_id,

        interaction_token

    )


    image = render_board(
        game
    )


    if game.mode == "bot":

        players_text = (

            f"**{game.player1_name}** "
            f"vs "
            f"**BurstSay**"

        )

    else:

        players_text = (

            f"**{game.player1_name}** "
            f"♔ vs ♚ "
            f"**{game.player2_name}**"

        )


    payload = {

        "content":
        content,

        "embeds": [

            {

                "title":
                "♟️ BurstSay Chess",

                "description": (

                    f"{players_text}\n\n"

                    f"**Turn:** "
                    f"{game.current_player_name}\n"

                    f"**Moves:** "
                    f"{len(game.move_history)}"

                ),

                "image": {

                    "url":
                    "attachment://chess.png"

                },

                "footer": {

                    "text":
                    "BurstSay Chess"

                }

            }

        ],

        "components":
        build_chess_components(
            game
        ),

        "attachments": [

            {

                "id":
                "0",

                "filename":
                "chess.png"

            }

        ]

    }


    try:

        response = requests.patch(

            webhook_url,

            data={

                "payload_json":
                json.dumps(
                    payload
                )

            },

            files={

                "files[0]": (

                    "chess.png",

                    image,

                    "image/png"

                )

            },

            timeout=30

        )


        if not response.ok:

            print(

                "Chess update failed:",

                response.status_code,

                response.text

            )


    except Exception as error:

        print(

            "Chess update exception:",

            repr(error)

        )


# ============================================================
# FIND GUILD MEMBER
# ============================================================

def find_guild_member(

    guild_id,

    username

):

    if not guild_id:

        return (

            None,

            "❌ **Player mode must be used inside a server.**\n"
            "Discord's guild member search is required to find the opponent."

        )


    username = username.strip()


    # --------------------------------------------------------
    # Mention support
    # --------------------------------------------------------

    if (

        username.startswith("<@")

        and

        username.endswith(">")

    ):

        clean_id = (

            username

            .replace(
                "<@",
                ""
            )

            .replace(
                "!",
                ""
            )

            .replace(
                ">",
                ""
            )

        )


        if clean_id.isdigit():

            url = (

                "https://discord.com/api/v10/guilds/"

                f"{guild_id}/members/"
                f"{clean_id}"

            )


            response = requests.get(

                url,

                headers={

                    "Authorization":
                    f"Bot {BOT_TOKEN}"

                },

                timeout=15

            )


            if response.ok:

                return (

                    response.json().get(
                        "user"
                    ),

                    None

                )


    # --------------------------------------------------------
    # Official Discord guild member search
    # --------------------------------------------------------

    url = (

        "https://discord.com/api/v10/guilds/"

        f"{guild_id}/members/search"

    )


    try:

        response = requests.get(

            url,

            params={

                "query":
                username,

                "limit":
                100

            },

            headers={

                "Authorization":
                f"Bot {BOT_TOKEN}"

            },

            timeout=15

        )


    except Exception as error:

        return (

            None,

            f"❌ Member search failed: `{error}`"

        )


    if not response.ok:

        return (

            None,

            (

                "❌ Discord couldn't search the server members.\n"

                f"HTTP `{response.status_code}`"

            )

        )


    members = response.json()


    matches = []


    wanted = username.lower()


    for member in members:

        user = member.get(
            "user",
            {}
        )


        actual_username = (

            user.get(
                "username"
            )
            or
            ""

        ).lower()


        global_name = (

            user.get(
                "global_name"
            )
            or
            ""

        ).lower()


        nickname = (

            member.get(
                "nick"
            )
            or
            ""

        ).lower()


        if (

            actual_username
            == wanted

            or

            global_name
            == wanted

            or

            nickname
            == wanted

        ):

            matches.append(
                user
            )


    if len(matches) == 1:

        return (
            matches[0],
            None
        )


    if len(matches) > 1:

        return (

            None,

            "❌ Multiple members matched that name. "
            "Use the exact username or @mention."

        )


    return (

        None,

        "❌ I couldn't find that player in this server.\n"
        "Use their exact Discord username or @mention."

    )


# ============================================================
# ERROR RESPONSE
# ============================================================

def error_response(
    message
):

    return jsonify({

        "type": 4,

        "data": {

            "content":
            message,

            "flags":
            64

        }

    })


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

    data = (
        request.get_json()
        or {}
    )


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


        user_name = get_user_name(
            data
        )


        # ====================================================
        # SAY
        # ====================================================

        if name == "say":

            return jsonify({

                "type": 4,

                "data": {

                    "content":
                    options.get(
                        "message",
                        ""
                    )

                }

            })


        # ====================================================
        # BURSTSAY
        # ====================================================

        if name == "burstsay":

            message = options.get(
                "message",
                ""
            )


            count = max(

                1,

                min(

                    int(
                        options.get(
                            "count",
                            1
                        )
                    ),

                    100

                )

            )


            return jsonify({

                "type": 4,

                "data": {

                    "content":
                    "\n".join(
                        [message] * count
                    )

                }

            })


        # ====================================================
        # GLAZE
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

                                "text":
                                "BurstSay • Completely unbiased. Probably."

                            }

                        }

                    ]

                }

            })


        # ====================================================
        # ABOUT
        # ====================================================

        if name == "about":

            return jsonify({

                "type": 4,

                "data": {

                    "embeds": [

                        {

                            "title":
                            "💥 BurstSay",

                            "description": (

                                "The ultimate Discord "
                                "utility app built to make "
                                "Discord a little more chaotic.\n\n"

                                "👑 **Created by White**\n"
                                "`likewhiteforever`\n\n"

                                "### 📜 Commands\n\n"

                                "💬 **/say**\n"
                                "Send a message.\n\n"

                                "💥 **/burstsay**\n"
                                "Repeat a message.\n\n"

                                "✨ **/glaze**\n"
                                "Glaze White.\n\n"

                                "♟️ **/chess**\n"
                                "Play against BurstSay or another player.\n\n"

                                "🧞 **/akinator**\n"
                                "Let BurstSay guess a character, animal, or object.\n\n"

                                "💣 **/nuke**\n"
                                "Send the nuke message.\n\n"

                                "ℹ️ **/about**\n"
                                "About BurstSay."

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
        # NUKE
        # ====================================================

        if name == "nuke":

            count = max(

                1,

                min(

                    int(
                        options.get(
                            "count",
                            1
                        )
                    ),

                    20

                )

            )


            threading.Thread(

                target=send_delayed_nuke,

                args=(

                    data.get(
                        "application_id"
                    ),

                    data.get(
                        "token"
                    ),

                    count

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 5

            })


        # ====================================================
        # AKINATOR
        # ====================================================

        if name == "akinator":

            selected_theme = options.get(
                "theme",
                "character"
            )


            theme = AKINATOR_THEMES.get(
                selected_theme
            )


            if theme is None:

                return error_response(
                    "❌ Invalid Akinator category."
                )


            if not user_id:

                return error_response(
                    "❌ Could not identify you."
                )


            if get_akinator_game(
                user_id
            ):

                return error_response(

                    "🧞 **You're already playing Akinator.**\n\n"

                    "Finish your current game first."

                )


            try:

                game = start_akinator(

                    user_id,

                    theme

                )

            except Exception as error:

                print(
                    "Akinator start error:",
                    repr(error)
                )

                return error_response(

                    "❌ **Akinator couldn't start.**\n\n"

                    "The Akinator service may be temporarily unavailable."

                )


            return jsonify({

                "type": 4,

                "data":
                akinator_question_data(

                    game,

                    user_id,

                    AKINATOR_THEME_NAMES[
                        theme
                    ],

                    intro=True

                )

            })


        # ====================================================
        # CHESS
        # ====================================================

        if name == "chess":

            return jsonify({

                "type": 4,

                "data": {

                    "content": (

                        "♟️ **BurstSay Chess**\n\n"

                        "Choose how you want to play."

                    ),

                    "components": [

                        {

                            "type": 1,

                            "components": [

                                {

                                    "type": 2,

                                    "style": 1,

                                    "label":
                                    "Play vs Bot",

                                    "emoji": {

                                        "name":
                                        "🤖"

                                    },

                                    "custom_id":
                                    "chess_mode_bot"

                                },

                                {

                                    "type": 2,

                                    "style": 2,

                                    "label":
                                    "Play vs Player",

                                    "emoji": {

                                        "name":
                                        "👤"

                                    },

                                    "custom_id":
                                    "chess_mode_player"

                                }

                            ]

                        }

                    ],

                    "flags":
                    64

                }

            })


    # ========================================================
    # COMPONENT
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


        user_name = get_user_name(
            data
        )


        if not user_id:

            return error_response(
                "❌ Could not identify you."
            )


        # ====================================================
        # AKINATOR ANSWERS
        # ====================================================

        if custom_id.startswith(
            "aki_answer:"
        ):

            parts = custom_id.split(
                ":"
            )


            if len(parts) != 3:

                return error_response(
                    "❌ Invalid Akinator button."
                )


            action = parts[1]

            button_user_id = parts[2]


            if str(user_id) != str(
                button_user_id
            ):

                return error_response(

                    "🔒 **This isn't your Akinator game.**\n"

                    "Only the player who started it can answer."

                )


            game = get_akinator_game(
                user_id
            )


            if not game:

                return error_response(

                    "❌ **Your Akinator game no longer exists.**\n\n"

                    "Start a new game with `/akinator`."

                )


            answer_map = {

                "yes":
                "y",

                "no":
                "n",

                "idk":
                "i",

                "probably":
                "p",

                "probably_not":
                "pn"

            }


            answer = answer_map.get(
                action
            )


            if answer is None:

                return error_response(
                    "❌ Invalid Akinator answer."
                )


            try:

                game.answer(
                    answer
                )

            except Exception as error:

                print(

                    "Akinator answer error:",

                    repr(error)

                )


                delete_akinator_game(
                    user_id
                )


                return error_response(

                    "❌ Akinator encountered an error.\n\n"

                    "Start a new game with `/akinator`."

                )


            try:

                progression = float(
                    getattr(
                        game,
                        "progression",
                        0
                    )
                )

            except Exception:

                progression = 0


            # ------------------------------------------------
            # MAKE A GUESS
            # ------------------------------------------------

            if (

                getattr(
                    game,
                    "finished",
                    False
                )

                or

                progression >= 85

            ):

                try:

                    game.win()

                except Exception as error:

                    print(

                        "Akinator win error:",

                        repr(error)

                    )


                    delete_akinator_game(
                        user_id
                    )


                    return error_response(

                        "❌ Akinator couldn't make a guess.\n\n"

                        "Start another game with `/akinator`."

                    )


                return jsonify({

                    "type": 7,

                    "data":
                    akinator_guess_data(

                        game,

                        user_id

                    )

                })


            # ------------------------------------------------
            # NEXT QUESTION
            # ------------------------------------------------

            theme = getattr(

                game,

                "theme",

                "c"

            )


            theme_name = (

                AKINATOR_THEME_NAMES.get(

                    theme,

                    "Akinator"

                )

            )


            return jsonify({

                "type": 7,

                "data":
                akinator_question_data(

                    game,

                    user_id,

                    theme_name

                )

            })


        # ====================================================
        # AKINATOR GUESS
        # ====================================================

        if custom_id.startswith(
            "aki_guess:"
        ):

            parts = custom_id.split(
                ":"
            )


            if len(parts) != 3:

                return error_response(
                    "❌ Invalid Akinator guess button."
                )


            result = parts[1]

            button_user_id = parts[2]


            if str(user_id) != str(
                button_user_id
            ):

                return error_response(

                    "🔒 **This isn't your Akinator game.**"

                )


            game = get_akinator_game(
                user_id
            )


            if not game:

                return error_response(

                    "❌ **Your Akinator game has expired.**"

                )


            # ------------------------------------------------
            # CORRECT
            # ------------------------------------------------

            if result == "yes":

                guessed_name = (

                    getattr(

                        game,

                        "name_proposition",

                        "your answer"

                    )

                )


                delete_akinator_game(
                    user_id
                )


                return jsonify({

                    "type": 7,

                    "data": {

                        "content": (

                            "🎯 **I GOT IT!**\n\n"

                            f"🧞 I guessed "
                            f"**{guessed_name}**.\n\n"

                            "Humanity remains predictable. 💀"

                        ),

                        "components":
                        []

                    }

                })


            # ------------------------------------------------
            # WRONG
            # ------------------------------------------------

            if result == "no":

                theme = getattr(

                    game,

                    "theme",

                    "c"

                )


                try:

                    new_game = (
                        akinator.Akinator()
                    )


                    new_game.start_game(
                        theme=theme
                    )


                    set_akinator_game(

                        user_id,

                        new_game

                    )


                    theme_name = (

                        AKINATOR_THEME_NAMES.get(

                            theme,

                            "Akinator"

                        )

                    )


                    return jsonify({

                        "type": 7,

                        "data":
                        akinator_question_data(

                            new_game,

                            user_id,

                            theme_name,

                            intro=False

                        )

                    })


                except Exception as error:

                    print(

                        "Akinator restart error:",

                        repr(error)

                    )


                    delete_akinator_game(
                        user_id
                    )


                    return error_response(

                        "❌ I couldn't continue the game.\n\n"

                        "Try `/akinator` again."

                    )


        # ====================================================
        # BOT MODE
        # ====================================================

        if custom_id == "chess_mode_bot":

            delete_game(
                user_id
            )


            game = create_game(

                player1_id=user_id,

                mode="bot",

                player1_name=user_name,

                player2_name="BurstSay"

            )


            if game.player_color == chess.BLACK:

                game.make_bot_move()


            threading.Thread(

                target=edit_chess_message,

                args=(

                    data.get(
                        "application_id"
                    ),

                    data.get(
                        "token"
                    ),

                    game,

                    chess_content(
                        game
                    )

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 5

            })


        # ====================================================
        # PLAYER MODE
        # ====================================================

        if custom_id == "chess_mode_player":

            return jsonify({

                "type": 9,

                "data": {

                    "custom_id":
                    "chess_player_modal",

                    "title":
                    "Play Against a Player",

                    "components": [

                        {

                            "type": 1,

                            "components": [

                                {

                                    "type": 4,

                                    "custom_id":
                                    "opponent_username",

                                    "label":
                                    "Opponent username",

                                    "style": 1,

                                    "placeholder":
                                    "Example: username",

                                    "required":
                                    True,

                                    "min_length":
                                    2,

                                    "max_length":
                                    100

                                }

                            ]

                        }

                    ]

                }

            })


        # ====================================================
        # ACCEPT
        # ====================================================

        if custom_id == "chess_accept":

            with PENDING_INVITES_LOCK:

                invite = (
                    PENDING_INVITES.get(
                        str(user_id)
                    )
                )


            if not invite:

                return error_response(

                    "❌ This chess invitation "
                    "has expired or was already used."

                )


            if invite["expires"] < time.time():

                with PENDING_INVITES_LOCK:

                    PENDING_INVITES.pop(
                        str(user_id),
                        None
                    )


                return error_response(

                    "❌ This chess invitation has expired."

                )


            challenger_id = (
                invite["challenger_id"]
            )


            challenger_name = (
                invite["challenger_name"]
            )


            opponent_name = (
                user_name
            )


            delete_game(
                challenger_id
            )


            delete_game(
                user_id
            )


            game = create_game(

                player1_id=
                challenger_id,

                player2_id=
                user_id,

                mode=
                "player",

                player1_name=
                challenger_name,

                player2_name=
                opponent_name

            )


            with PENDING_INVITES_LOCK:

                PENDING_INVITES.pop(

                    str(user_id),

                    None

                )


            threading.Thread(

                target=edit_chess_message,

                args=(

                    data.get(
                        "application_id"
                    ),

                    data.get(
                        "token"
                    ),

                    game,

                    chess_content(
                        game
                    )

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 5

            })


        # ====================================================
        # DECLINE
        # ====================================================

        if custom_id == "chess_decline":

            with PENDING_INVITES_LOCK:

                PENDING_INVITES.pop(

                    str(user_id),

                    None

                )


            return jsonify({

                "type": 4,

                "data": {

                    "content":
                    "❌ Chess invitation declined.",

                    "components":
                    []

                }

            })


        # ====================================================
        # GET GAME
        # ====================================================

        game = get_game(
            user_id
        )


        # ----------------------------------------------------
        # SECURITY CHECK
        # ----------------------------------------------------

        if not game:

            return error_response(

                "🔒 **This isn't your chess game.**\n"
                "Only the two players can control it."

            )


        if not game.is_player(
            user_id
        ):

            return error_response(

                "🔒 **This isn't your chess game.**\n"
                "Only the two players can control it."

            )


        # ====================================================
        # SOURCE
        # ====================================================

        if custom_id == "chess_source":

            if not game.player_turn_for(
                user_id
            ):

                return error_response(

                    "⏳ **It's the other player's turn.**"

                )


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

                return error_response(
                    "❌ Select a piece."
                )


            try:

                square = int(
                    values[0]
                )

            except ValueError:

                return error_response(
                    "❌ Invalid square."
                )


            piece = game.board.piece_at(
                square
            )


            if not piece:

                return error_response(

                    "❌ There isn't a piece there."

                )


            if piece.color != game.board.turn:

                return error_response(

                    "❌ That's not your piece."

                )


            legal = (
                game.legal_destinations(
                    square
                )
            )


            if not legal:

                return error_response(

                    "❌ That piece has no legal moves."

                )


            game.selected_square = square


            threading.Thread(

                target=edit_chess_message,

                args=(

                    data.get(
                        "application_id"
                    ),

                    data.get(
                        "token"
                    ),

                    game,

                    (

                        f"♟️ **{square_name(square)} "
                        "selected.**\n"
                        "Choose a destination."

                    )

                ),

                daemon=True

            ).start()


            return jsonify({

                "type": 6

            })


        # ====================================================
        # DESTINATION
        # ====================================================

        if custom_id.startswith(
            "chess_destination_"
        ):

            if not game.player_turn_for(
                user_id
            ):

                return error_response(

                    "⏳ **It's the other player's turn.**"

                )


            if game.selected_square is None:

                return error_response(

                    "❌ Select a piece first."

                )


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

                return error_response(
                    "❌ Select a destination."
                )


            try:

                to_square = int(
                    values[0]
                )

            except ValueError:

                return error_response(
                    "❌ Invalid destination."
                )


            from_square = (
                game.selected_square
            )


            success, result = (
                game.make_player_move(

                    user_id,

                    from_square,

                    to_square

                )
            )


            game.selected_square = None


            if not success:

                threading.Thread(

                    target=edit_chess_message,

                    args=(

                        data.get(
                            "application_id"
                        ),

                        data.get(
                            "token"
                        ),

                        game,

                        f"❌ {result}"

                    ),

                    daemon=True

                ).start()


                return jsonify({

                    "type": 6

                })


            # ------------------------------------------------
            # Bot mode
            # ------------------------------------------------

            if (

                game.mode == "bot"

                and

                not game.finished

            ):

                bot_move = (
                    game.make_bot_move()
                )


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


            # ------------------------------------------------
            # Player mode
            # ------------------------------------------------

            else:

                content = chess_content(
                    game
                )


                if game.finished:

                    content = (
                        chess_content(
                            game
                        )
                    )

                else:

                    content = (

                        f"♟️ **{game.last_player_name} "
                        f"played `{result}`.**\n\n"

                        f"{chess_content(game)}"

                    )


            threading.Thread(

                target=edit_chess_message,

                args=(

                    data.get(
                        "application_id"
                    ),

                    data.get(
                        "token"
                    ),

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

            game.resign(
                user_id
            )


            threading.Thread(

                target=edit_chess_message,

                args=(

                    data.get(
                        "application_id"
                    ),

                    data.get(
                        "token"
                    ),

                    game,

                    (

                        f"🏳️ **{user_name} resigned.**\n\n"

                        f"🏆 **{game.winner_name} wins!**"

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
                game.player1_id
            )


            if game.player2_id:

                delete_game(
                    game.player2_id
                )


            return jsonify({

                "type": 4,

                "data": {

                    "content": (

                        "♟️ The previous game has ended.\n"
                        "Use `/chess` to start another game."

                    ),

                    "components":
                    []

                }

            })


    # ========================================================
    # MODAL SUBMIT
    # ========================================================

    if data.get("type") == 5:

        custom_id = (

            data.get(
                "data",
                {}
            ).get(
                "custom_id"
            )

        )


        if custom_id == "chess_player_modal":

            challenger_id = get_user_id(
                data
            )


            challenger_name = get_user_name(
                data
            )


            guild_id = data.get(
                "guild_id"
            )


            modal_components = (

                data.get(
                    "data",
                    {}
                ).get(
                    "components",
                    []
                )

            )


            opponent_username = ""


            try:

                opponent_username = (

                    modal_components[0]

                    ["components"][0]

                    ["value"]

                    .strip()

                )

            except Exception:

                pass


            if not opponent_username:

                return error_response(

                    "❌ Enter an opponent username."

                )


            opponent, error = (
                find_guild_member(

                    guild_id,

                    opponent_username

                )
            )


            if error:

                return error_response(
                    error
                )


            opponent_id = str(
                opponent["id"]
            )


            if opponent_id == str(
                challenger_id
            ):

                return error_response(

                    "❌ You can't challenge yourself."

                )


            if opponent.get(
                "bot"
            ):

                return error_response(

                    "❌ You can't challenge a bot."

                )


            if get_game(
                challenger_id
            ):

                return error_response(

                    "❌ You are already in a chess game."

                )


            if get_game(
                opponent_id
            ):

                return error_response(

                    "❌ That player is already in a chess game."

                )


            with PENDING_INVITES_LOCK:

                PENDING_INVITES[
                    opponent_id
                ] = {

                    "challenger_id":
                    str(challenger_id),

                    "challenger_name":
                    challenger_name,

                    "guild_id":
                    guild_id,

                    "expires":
                    time.time() + 300

                }


            return jsonify({

                "type": 4,

                "data": {

                    "content": (

                        f"♟️ **Chess Challenge!**\n\n"

                        f"**{challenger_name}** "
                        f"has challenged "
                        f"<@{opponent_id}> "
                        f"to a chess game.\n\n"

                        f"<@{opponent_id}> "
                        f"has **5 minutes** to accept."

                    ),

                    "components": [

                        {

                            "type": 1,

                            "components": [

                                {

                                    "type": 2,

                                    "style": 3,

                                    "label":
                                    "Accept",

                                    "custom_id":
                                    "chess_accept"

                                },

                                {

                                    "type": 2,

                                    "style": 4,

                                    "label":
                                    "Decline",

                                    "custom_id":
                                    "chess_decline"

                                }

                            ]

                        }

                    ]

                }

            )


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
