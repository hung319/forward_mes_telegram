# config.py
import os

# --- Telegram API Credentials ---
API_ID = int(os.environ.get("API_ID", "YOUR_API_ID_HERE"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH_HERE")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# --- MongoDB Configuration ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "telegram_forward_bot"
COLLECTION_NAME = "forward_rules"
# Thêm collection mới để lưu trữ user sessions
USER_SESSIONS_COLLECTION_NAME = "user_sessions"

# --- Logging Configuration (Tùy chọn) ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# --- Admin User IDs (Quan trọng để kiểm soát ai có thể dùng lệnh) ---
# Thêm ID Telegram của bạn vào đây để chỉ bạn mới có thể dùng các lệnh admin
ADMIN_USER_IDS = [123456789] # Thay bằng ID Telegram của bạn
