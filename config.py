
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

def load_env_file():
    env_file = BASE_DIR / ".env"

    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

# Application Identity
APP_NAME = "NEO AI"
WINDOW_TITLE = "NEO AI Assistant"
TAGLINE = "Your Local AI PC Assistant"

NEO_NAME = os.getenv("NEO_NAME") or os.getenv("ORION_NAME", "NEO")
ORION_NAME = NEO_NAME  # Backward compatibility alias

OLLAMA_HOST = (
    os.getenv("NEO_OLLAMA_HOST")
    or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
).rstrip("/")

OLLAMA_MODEL = (
    os.getenv("NEO_OLLAMA_MODEL")
    or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
)

API_HOST = (
    os.getenv("NEO_API_HOST")
    or os.getenv("ORION_API_HOST", "127.0.0.1")
)

try:
    _port_str = os.getenv("NEO_API_PORT") or os.getenv("ORION_API_PORT", "8765")
    API_PORT = int(_port_str)
except ValueError:
    API_PORT = 8765

VOICE_ENABLED = os.getenv(
    "VOICE_ENABLED",
    "true"
).lower() in {"1", "true", "yes", "on"}

try:
    _mic_env = (
        os.getenv("NEO_MICROPHONE_INDEX")
        or os.getenv("MICROPHONE_INDEX", "")
    ).strip()
    MICROPHONE_INDEX = int(_mic_env) if _mic_env else None
except ValueError:
    MICROPHONE_INDEX = None