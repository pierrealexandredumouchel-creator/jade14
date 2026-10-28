from pathlib import Path

from core.config import PERSONALITY_DIR


ALIASES = {
    "anya": "anya",
    "millie": "millie",
    "tanya": "tanya24",
    "tanya24": "tanya24",
    "tanya24_": "tanya24",
    "jade": "jade14",
    "jade14": "jade14",
    "christine": "christine24",
    "christin24": "christine24",
    "christine24": "christine24",
}


DEFAULT_PERSONA = """
Tu es un bot IRC du Ghost Royale.
Réponds brièvement en français québécois.
Ne réponds jamais aux autres bots.
Évite le flood et les répétitions.
""".strip()


def normalize_bot(bot_name):
    key = str(bot_name).strip().casefold()
    return ALIASES.get(key, key)


def persona_path(bot_name):
    normalized = normalize_bot(bot_name)
    return Path(PERSONALITY_DIR) / f"{normalized}.txt"


def load_persona(bot_name):
    path = persona_path(bot_name)

    try:
        persona = path.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return DEFAULT_PERSONA

    return persona or DEFAULT_PERSONA
