import os

API_ID = int(os.getenv("API_ID", 123456))  # Có thể để mặc định 123456 hoặc bỏ luôn default nếu muốn
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "forward_bot")

# ADMIN_IDS lưu dưới dạng chuỗi, ví dụ "123456,78910", sau đó chuyển thành list[int]
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
