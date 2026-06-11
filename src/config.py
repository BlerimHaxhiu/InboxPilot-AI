import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(_BASE, "data", "inboxpilot.db")
DEMO_EMAILS_PATH = os.path.join(_BASE, "data", "demo_emails.json")

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
HAS_OPENAI: bool = bool(OPENAI_API_KEY)
PROCESSING_MODE: str = "OpenAI-enhanced mode" if HAS_OPENAI else "Rule-based mode"
APP_MODE: str = os.environ.get("APP_MODE", "demo")
