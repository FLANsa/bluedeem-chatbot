"""Configuration module for BlueDeem Chatbot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL_INTENT = os.getenv("LLM_MODEL_INTENT", "gpt-4.1-nano")
LLM_MODEL_AGENT = os.getenv("LLM_MODEL_AGENT", "gpt-4.1-mini")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bluedeem.db")
DB_PATH = BASE_DIR / "bluedeem.db" if "sqlite" in DATABASE_URL else None

# Cache settings
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour

# Platform webhook secrets
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
INSTAGRAM_WEBHOOK_SECRET = os.getenv("INSTAGRAM_WEBHOOK_SECRET", "")
TIKTOK_WEBHOOK_SECRET = os.getenv("TIKTOK_WEBHOOK_SECRET", "")

# Google Apps Script
GOOGLE_APPS_SCRIPT_URL = os.getenv("GOOGLE_APPS_SCRIPT_URL", "")

# Google Sheets
GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")  # Spreadsheet ID
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")  # Path to credentials JSON or service account email
GOOGLE_SHEETS_SHEET_NAMES = {
    "doctors": os.getenv("GOOGLE_SHEETS_DOCTORS_SHEET", "01_doctors"),
    "branches": os.getenv("GOOGLE_SHEETS_BRANCHES_SHEET", "02_branches"),
    "services": os.getenv("GOOGLE_SHEETS_SERVICES_SHEET", "03_services"),
    "availability": os.getenv("GOOGLE_SHEETS_AVAILABILITY_SHEET", "04_doctor_availability"),
}

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Asia/Riyadh")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]

# Validation - will be checked when OpenAI client is initialized

