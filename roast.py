import os
import re
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


# ============================================================
# CONFIG
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from .env"
    )


MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)

DB_PATH = os.getenv(
    "ROAST_DB_PATH",
    "data/roasts.db"
)

MAX_HISTORY = 40
MAX_GENERATION_ATTEMPTS = 3


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    directory = os.path.dirname(DB_PATH)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    connection = sqlite3.connect(
        DB_PATH
    )

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


# ============================================================
# TEXT NORMALIZATION
# ============================================================

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


# ============================================================
# SIMILARITY
# ============================================================

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


# ============================================================
# CLEAN GEMINI OUTPUT
# ============================================================

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


# ============================================================
# PROMPT
# ============================================================

def build_prompt(
    target_id,
    previous_roasts
):

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
the Discord user with ID {target_id}.

The roast should sound like something a clever person
would spontaneously say in a Discord conversation.

IMPORTANT STYLE RULES:

- Be witty, sharp, and conversational.
- Make the joke feel specific and intentional.
- Avoid generic AI roast templates.
- Avoid repetitive "you're the human equivalent of..."
  constructions.
- Avoid repetitive "bro is..." constructions.
- Avoid generic insults with no joke behind them.
- Don't explain the joke.
- Don't say "here's your roast".
- Don't mention being an AI.
- Keep it to 1 or 2 sentences.
- Make the punchline arrive naturally.
- Vary sentence structure and comedic technique.
- Don't use the same metaphor repeatedly.
- Don't simply swap a few words from an old roast.
- Keep it playful rather than genuinely hateful.
- Do not target protected or sensitive personal traits.

Previous roasts used for this target:

{history_text}

Your new roast MUST feel meaningfully different from
all of the previous roasts.

Return ONLY the roast.
"""


# ============================================================
# GENERATION
# ============================================================

def generate_candidate(
    target_id,
    previous_roasts
):

    prompt = build_prompt(
        target_id,
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


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def generate_roast(target_id):

    target_id = str(
        target_id
    ).strip()

    previous_roasts = get_previous_roasts(
        target_id
    )

    best_candidate = None

    for attempt in range(
        MAX_GENERATION_ATTEMPTS
    ):

        candidate = generate_candidate(
            target_id,
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

        # One final generation with stronger
        # uniqueness instructions.
        emergency_prompt = f"""
Write ONE completely original, short Discord roast.

Target Discord user ID:
{target_id}

Do NOT reuse any idea, metaphor, punchline,
structure, or wording from these previous roasts:

{chr(10).join(previous_roasts)}

Make it clever, conversational, and concise.

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
