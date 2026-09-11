import os
import re
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from .env"
    )


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from .env"
    )


MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)


DB_PATH = os.getenv(
    "ROAST_DB_PATH",
    "data/roasts.db"
)


DISCORD_API = "https://discord.com/api/v10"

MAX_HISTORY = 40
MAX_GENERATION_ATTEMPTS = 3


client = genai.Client(
    api_key=GEMINI_API_KEY
)


def get_connection():
    directory = os.path.dirname(DB_PATH)

    if directory:
        os.makedirs(directory, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS roasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id TEXT NOT NULL,
            roast TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.commit()

    return connection


def get_previous_roasts(target_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT roast
            FROM roasts
            WHERE target_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                str(target_id),
                MAX_HISTORY
            )
        )

        return [
            row[0]
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def save_roast(target_id, roast):
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO roasts
            (
                target_id,
                roast,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                str(target_id),
                roast,
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
        )

        connection.commit()

    finally:
        connection.close()


def discord_headers():
    return {
        "Authorization":
            f"Bot {DISCORD_TOKEN}",

        "Content-Type":
            "application/json",

        "User-Agent":
            "BurstSay/1.0"
    }


def get_public_profile(target_id):
    response = requests.get(
        f"{DISCORD_API}/users/{target_id}",
        headers=discord_headers(),
        timeout=15
    )

    if response.status_code == 404:
        raise RuntimeError(
            "That Discord user does not exist."
        )

    if response.status_code == 401:
        raise RuntimeError(
            "BurstSay's Discord token was rejected."
        )

    if not response.ok:
        raise RuntimeError(
            "Discord returned HTTP "
            f"{response.status_code}."
        )

    user = response.json()

    return {
        "id": user.get("id"),
        "username": user.get(
            "username",
            "Unknown"
        ),
        "global_name": user.get(
            "global_name"
        ),
        "bot": bool(
            user.get("bot", False)
        )
    }


def get_server_context(guild_id, target_id):
    if not guild_id:
        return {}

    response = requests.get(
        f"{DISCORD_API}/guilds/"
        f"{guild_id}/members/{target_id}",
        headers=discord_headers(),
        timeout=15
    )

    if not response.ok:
        return {}

    member = response.json()

    return {
        "nickname": member.get("nick")
    }


def normalize_text(text):
    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def words(text):
    return set(
        normalize_text(text).split()
    )


def similarity(a, b):
    a_normalized = normalize_text(a)
    b_normalized = normalize_text(b)

    sequence_score = SequenceMatcher(
        None,
        a_normalized,
        b_normalized
    ).ratio()

    a_words = words(a)
    b_words = words(b)

    if not a_words or not b_words:
        word_score = 0.0

    else:
        intersection = len(
            a_words & b_words
        )

        union = len(
            a_words | b_words
        )

        word_score = (
            intersection / union
            if union
            else 0.0
        )

    return max(
        sequence_score,
        word_score
    )


def is_too_similar(
    candidate,
    previous_roasts
):
    for previous in previous_roasts:

        if similarity(
            candidate,
            previous
        ) >= 0.72:

            return True

    return False


def clean_roast(text):
    if not text:
        return ""

    text = text.strip()

    text = re.sub(
        r"^```.*?\n",
        "",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"\n```$",
        "",
        text
    )

    text = text.strip()

    text = re.sub(
        r"^(roast|roast:)\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.strip(
        "\"' "
    )

    return text


def build_prompt(
    profile,
    previous_roasts
):
    username = profile.get(
        "username",
        "Unknown"
    )

    global_name = profile.get(
        "global_name"
    )

    nickname = profile.get(
        "nickname"
    )

    is_bot = profile.get(
        "bot",
        False
    )

    profile_lines = [
        f"Username: {username}"
    ]

    if global_name:
        profile_lines.append(
            f"Display name: {global_name}"
        )

    if nickname:
        profile_lines.append(
            f"Server nickname: {nickname}"
        )

    profile_lines.append(
        f"Account is a bot: {'yes' if is_bot else 'no'}"
    )

    profile_context = "\n".join(
        profile_lines
    )

    history_text = "\n".join(
        f"- {roast}"
        for roast in previous_roasts
    )

    if not history_text:
        history_text = (
            "(No previous roasts. "
            "You have a completely blank slate.)"
        )

    return f"""
You are the roast writer for a Discord bot.

Generate a short, genuinely funny roast aimed at
the Discord user described below.

PUBLIC DISCORD PROFILE:

{profile_context}

Use the available profile information naturally.
The username or display name can inspire wordplay,
but do not pretend you know things that are not provided.

STYLE:

- Be witty, sharp, and conversational.
- Make the joke feel intentional.
- Sound like a clever person talking in Discord.
- Avoid generic AI roast templates.
- Avoid repetitive "you're the human equivalent of..."
  constructions.
- Avoid repetitive "bro is..." constructions.
- Avoid generic insults with no joke behind them.
- Don't explain the joke.
- Don't mention being an AI.
- Keep it to 1 or 2 sentences.
- Make the punchline arrive naturally.
- Vary sentence structure.
- Vary comedic techniques.
- Don't reuse the same metaphor repeatedly.
- Don't simply swap a few words from an old roast.
- Keep it playful rather than genuinely hateful.
- Do not target protected or sensitive personal traits.
- Do not invent private information.
- Do not make claims about someone's real-life identity,
  health, family, location, or other sensitive information.

PREVIOUS ROASTS:

{history_text}

Your new roast MUST feel meaningfully different from
all previous roasts.

Return ONLY the roast.
"""


def generate_candidate(
    profile,
    previous_roasts
):
    prompt = build_prompt(
        profile,
        previous_roasts
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=1.15,
            candidate_count=1,
            max_output_tokens=120
        )
    )

    roast = clean_roast(
        response.text
    )

    return roast


def generate_roast(
    target_id,
    guild_id=None
):
    target_id = str(
        target_id
    ).strip()

    profile = get_public_profile(
        target_id
    )

    server_context = get_server_context(
        guild_id,
        target_id
    )

    profile.update(
        server_context
    )

    previous_roasts = get_previous_roasts(
        target_id
    )

    best_candidate = None

    for attempt in range(
        MAX_GENERATION_ATTEMPTS
    ):
        candidate = generate_candidate(
            profile,
            previous_roasts
        )

        if not candidate:
            continue

        if is_too_similar(
            candidate,
            previous_roasts
        ):
            continue

        best_candidate = candidate
        break

    if not best_candidate:
        emergency_prompt = f"""
Write ONE completely original, short Discord roast.

Target username:
{profile.get("username", "Unknown")}

Display name:
{profile.get("global_name", "Unknown")}

Server nickname:
{profile.get("nickname", "None")}

Do NOT reuse any idea, metaphor, punchline,
structure, or wording from these previous roasts:

{chr(10).join(previous_roasts)}

Make it clever, conversational, playful,
and concise.

Return ONLY the roast.
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=emergency_prompt,
            config=types.GenerateContentConfig(
                temperature=1.25,
                candidate_count=1,
                max_output_tokens=120
            )
        )

        best_candidate = clean_roast(
            response.text
        )

    if not best_candidate:
        raise RuntimeError(
            "Gemini did not return a roast."
        )

    save_roast(
        target_id,
        best_candidate
    )

    return best_candidate
