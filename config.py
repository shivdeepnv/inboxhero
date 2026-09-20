import os

from dotenv import load_dotenv

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("INBOXHERO_MODEL", "claude-haiku-4-5-20251001")
REQUEST_DELAY_S = float(os.getenv("REQUEST_DELAY_S", "1.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))


def require_api_key():
    if not ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
    return ANTHROPIC_API_KEY
