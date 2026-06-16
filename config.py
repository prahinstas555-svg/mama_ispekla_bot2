import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_ID = int(os.getenv("MANAGER_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")