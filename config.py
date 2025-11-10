import os
from dotenv import load_dotenv

# Nạp biến từ file .env vào môi trường
load_dotenv()

API_ID = int(os.getenv("API_ID", 123456))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "forward_bot")

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
