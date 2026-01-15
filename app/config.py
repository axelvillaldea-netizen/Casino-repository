import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Configuration Database
DB_NAME = os.getenv("DB_NAME", "casino_final_cut.db")

# Configuration Logs
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
