from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PERSONALITY_DIR = BASE_DIR / "personalities"
STATE_DIR = BASE_DIR / "state"
LOG_DIR = BASE_DIR / "logs"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.1:latest"
OLLAMA_TIMEOUT = 20
OLLAMA_KEEP_ALIVE = "30m"

MASTER_NICK = "alxd"

MASTER_HOSTS = (
    "Alerion.users.undernet.org",
    "alxd.kekistan.faith",
)

BOT_NAMES = (
    "anya",
    "jade14",
    "christine24",
    "tanya24",
    "millie",
)
