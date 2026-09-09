import os
import requests
from dotenv import load_dotenv

load_dotenv()

APPLICATION_ID = os.getenv("APPLICATION_ID")
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if not APPLICATION_ID:
    raise RuntimeError("APPLICATION_ID is missing from .env")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing from .env")

url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"

commands = [
    {
        "name": "say",
        "description": "Send a message",
        "integration_types": [1],
        "contexts": [0, 1, 2],
        "options": [
            {
                "name": "message",
                "description": "The message to send",
                "type": 3,
                "required": True,
            }
        ],
    },
    {
        "name": "burstsay",
        "description": "Send a message multiple times",
        "integration_types": [1],
        "contexts": [0, 1, 2],
        "options": [
            {
                "name": "message",
                "description": "The message to send",
                "type": 3,
                "required": True,
            },
            {
                "name": "count",
                "description": "Number of repetitions",
                "type": 4,
                "required": True,
                "min_value": 1,
                "max_value": 10,
            },
        ],
    },
]

response = requests.put(
    url,
    headers={
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json",
    },
    json=commands,
)

print(response.status_code)
print(response.text)

response.raise_for_status()
print("Commands registered successfully!")
