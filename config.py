import os
from dotenv import load_dotenv

# Nạp biến từ file .env vào môi trường
load_dotenv()

# ============ TELEGRAM API ============
API_ID = int(os.getenv("API_ID", 123456))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# ============ DATABASE ============
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "forward_bot")

# ============ ADMIN ============
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))

# ============ LOGGER (Message ID Logging) ============
LOG_FILE = os.getenv("LOG_FILE", "message_ids.log")

# ============ SYNC (Database Sync) ============
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300))  # seconds (default: 5 minutes)

# ============ REALTIME FORWARD ============
REALTIME_CHECK_INTERVAL = int(os.getenv("REALTIME_CHECK_INTERVAL", 3))  # seconds
REALTIME_BATCH_SIZE = int(os.getenv("REALTIME_BATCH_SIZE", 10))  # messages per batch

# ============ FORWARD OPTIONS (Defaults) ============
DEFAULT_REMOVE_CAPTION = os.getenv("DEFAULT_REMOVE_CAPTION", "false").lower() == "true"
DEFAULT_REMOVE_FORWARD_HEADER = (
    os.getenv("DEFAULT_REMOVE_FORWARD_HEADER", "false").lower() == "true"
)
DEFAULT_MIN_DURATION = int(os.getenv("DEFAULT_MIN_DURATION", 0))  # seconds
DEFAULT_MAX_DURATION = int(os.getenv("DEFAULT_MAX_DURATION", 0))  # 0 = no limit
DEFAULT_MIN_FILE_SIZE = int(os.getenv("DEFAULT_MIN_FILE_SIZE", 0))  # bytes
DEFAULT_MAX_FILE_SIZE = int(os.getenv("DEFAULT_MAX_FILE_SIZE", 0))  # 0 = no limit

# ============ DEFAULT MEDIA TYPES ============
# Comma-separated: video,photo,document,audio,voice,video_note,sticker,animation,text
DEFAULT_MEDIA_TYPES = os.getenv("DEFAULT_MEDIA_TYPES", "all").split(",")

# ============ CONTENT FILTERS (Defaults) ============
DEFAULT_REQUIRE_CAPTION = (
    os.getenv("DEFAULT_REQUIRE_CAPTION", "false").lower() == "true"
)
DEFAULT_REQUIRE_HASHTAGS = (
    os.getenv("DEFAULT_REQUIRE_HASHTAGS", "false").lower() == "true"
)
# Comma-separated block words
DEFAULT_BLOCK_LIST = (
    os.getenv("DEFAULT_BLOCK_LIST", "").split(",")
    if os.getenv("DEFAULT_BLOCK_LIST")
    else []
)

# ============ SESSIONS FOLDER ============
SESSIONS_FOLDER = os.getenv("SESSIONS_FOLDER", "sessions")

# ============ RATE LIMITING ============
FLOOD_WAIT_DELAY = int(os.getenv("FLOOD_WAIT_DELAY", 5))  # seconds to wait on FloodWait
MESSAGE_DELAY = float(os.getenv("MESSAGE_DELAY", 0.5))  # seconds between messages
