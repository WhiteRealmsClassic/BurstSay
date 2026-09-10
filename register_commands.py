import os
import requests

from dotenv import load_dotenv


load_dotenv()


APPLICATION_ID = os.getenv("APPLICATION_ID")
BOT_TOKEN = os.getenv("DISCORD_TOKEN")


if not APPLICATION_ID:
    raise RuntimeError(
        "APPLICATION_ID is missing from .env"
    )


if not BOT_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from .env"
    )


url = (
    f"https://discord.com/api/v10/"
    f"applications/{APPLICATION_ID}/commands"
)


commands = [

    # ========================================================
    # /say
    # ========================================================

    {
        "name": "say",

        "description":
        "Send a message",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2],

        "options": [

            {
                "name":
                "message",

                "description":
                "The message to send",

                "type":
                3,

                "required":
                True
            }

        ]
    },


    # ========================================================
    # /burstsay
    # ========================================================

    {
        "name": "burstsay",

        "description":
        "Send a message multiple times",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2],

        "options": [

            {
                "name":
                "message",

                "description":
                "The message to send",

                "type":
                3,

                "required":
                True
            },

            {
                "name":
                "count",

                "description":
                "Number of repetitions",

                "type":
                4,

                "required":
                True,

                "min_value":
                1,

                "max_value":
                100
            }

        ]
    },


    # ========================================================
    # /glaze
    # ========================================================

    {
        "name": "glaze",

        "description":
        "Glaze White",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2]
    },


    # ========================================================
    # /about
    # ========================================================

    {
        "name": "about",

        "description":
        "Learn about BurstSay",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2]
    },


    # ========================================================
    # /nuke
    # ========================================================

    {
        "name": "nuke",

        "description":
        "Deploy the Whiteify Bot nuke",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2],

        "options": [

            {
                "name":
                "count",

                "description":
                "Number of times to repeat the nuke message",

                "type":
                4,

                "required":
                True,

                "min_value":
                1,

                "max_value":
                20
            }

        ]
    },


    # ========================================================
    # /chess
    # ========================================================

    {
        "name": "chess",

        "description":
        "Play chess",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2]
    },


    # ========================================================
    # /akinator
    # ========================================================

    {
        "name": "akinator",

        "description":
        "Let Akinator guess what you're thinking of",

        "integration_types":
        [1],

        "contexts":
        [0, 1, 2],

        "options": [

            {
                "name":
                "type",

                "description":
                "What are you thinking of?",

                "type":
                3,

                "required":
                True,

                "choices": [

                    {
                        "name":
                        "Character",

                        "value":
                        "characters"
                    },

                    {
                        "name":
                        "Animal",

                        "value":
                        "animals"
                    },

                    {
                        "name":
                        "Object",

                        "value":
                        "objects"
                    }

                ]
            }

        ]
    }

]


# ============================================================
# REGISTER
# ============================================================

print(
    "Registering BurstSay commands..."
)


response = requests.put(

    url,

    headers={

        "Authorization":
        f"Bot {BOT_TOKEN}",

        "Content-Type":
        "application/json"

    },

    json=commands,

    timeout=30

)


print(
    f"Discord response: "
    f"{response.status_code}"
)


print(
    response.text
)


response.raise_for_status()


print(
    f"Successfully registered "
    f"{len(commands)} commands!"
)


print(
    "Commands:"
)


for command in commands:

    print(
        f"  /{command['name']}"
    )
