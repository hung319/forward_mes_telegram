import os
import asyncio
import logging
import pickle
from typing import Optional, Any

from pyrogram import Client, filters, idle
from pyrogram.errors import (
    FloodWait, PeerIdInvalid, UserNotParticipant,
    ChannelInvalid, SessionExpired
)
from pyrogram.storage.storage import Storage

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.binary import Binary

# --- Import cấu hình từ config.py ---
try:
    import config
except ImportError:
    print("Lỗi: Không tìm thấy file config.py. Vui lòng tạo file config.py với các biến cần thiết.")
    exit(1)

# Cấu hình logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Khởi tạo MongoDB Client ---
mongo_client = None
try:
    mongo_client = MongoClient(config.MONGO_CONNECTION_STRING)
    mongo_client.admin.command('ping')
    db = mongo_client[config.DB_NAME]
    forward_rules_collection = db[config.COLLECTION_NAME]
    user_sessions_collection = db[config.USER_SESSIONS_COLLECTION_NAME]
    logger.info("Đã kết nối thành công tới MongoDB!")
except ConnectionFailure as e:
    logger.error(f"Không thể kết nối tới MongoDB: {e}")
    logger.error("Vui lòng đảm bảo MongoDB đang chạy và MONGO_CONNECTION_STRING là chính xác.")
    exit(1)
except OperationFailure as e:
    logger.error(f"Lỗi thao tác MongoDB: {e}")
    exit(1)
except AttributeError:
    logger.error("Lỗi: Biến cấu hình MongoDB bị thiếu trong file config.py.")
    exit(1)


# --- Custom MongoDB Storage cho Pyrogram v2.x ---
class MongoSessionStorage(Storage):
    def __init__(self, name: str, collection):
        super().__init__(name)
        self.collection = collection
        self._session_data = self._load_session()

    def _load_session(self) -> dict:
        stored_data = self.collection.find_one({"_id": self.name})
        if stored_data and "data" in stored_data:
            try:
                return pickle.loads(stored_data["data"])
            except pickle.UnpicklingError:
                logger.error(f"Không thể giải mã session data cho '{self.name}'. Tạo session mới.")
                return {}
        return {}

    def _save_session(self):
        if not self._session_data:
            self.collection.delete_one({"_id": self.name})
        else:
            self.collection.update_one(
                {"_id": self.name},
                {"$set": {"data": Binary(pickle.dumps(self._session_data))}},
                upsert=True
            )

    async def open(self): pass
    async def close(self): pass
    async def update(self): pass

    async def delete(self):
        self._session_data = {}
        self._save_session()
        logger.info(f"Đã xóa session '{self.name}' khỏi MongoDB.")

    async def _get(self, key: str, default: Any = None) -> Any:
        return self._session_data.get(key, default)

    async def _set(self, key: str, value: Any):
        self._session_data[key] = value
        self._save_session()

    async def _delete(self, key: str):
        if key in self._session_data:
            del self._session_data[key]
            self._save_session()

    async def get_dc(self) -> int: return await self._get("dc_id", 2)
    async def set_dc(self, value: int): await self._set("dc_id", value)
    async def get_auth_key(self): return await self._get("auth_key")
    async def set_auth_key(self, value): await self._set("auth_key", value)
    async def get_test_mode(self) -> bool: return await self._get("test_mode", False)
    async def set_test_mode(self, value: bool): await self._set("test_mode", value)
    async def get_user_id(self) -> Optional[int]: return await self._get("user_id")
    async def set_user_id(self, value: int): await self._set("user_id", value)
    async def get_date(self) -> int: return await self._get("date", 0)
    async def set_date(self, value: int): await self._set("date", value)

# --- Khởi tạo Clients Pyrogram ---
bot_client = Client(
    "my_forward_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

user_session_storage = MongoSessionStorage("my_user_session", user_sessions_collection)
user_client = Client(
    name="my_user_session",
    storage=user_session_storage,
    api_id=config.API_ID,
    api_hash=config.API_HASH
)

# --- Biến trạng thái Scan ---
scanning_tasks = {}

# --- Decorator để giới hạn lệnh cho admin ---
def admin_only(func):
    async def wrapper(client, message):
        if message.from_user.id not in config.ADMIN_USER_IDS:
            await message.reply_text("Bạn không có quyền sử dụng lệnh này.")
            logger.warning(f"Người dùng {message.from_user.id} ({message.from_user.first_name}) đã cố gắng sử dụng lệnh admin: {message.text}")
            return
        await func(client, message)
    return wrapper

# --- Hàm hỗ trợ ---
async def get_chat_id_from_input(client, user_input):
    if isinstance(user_input, int): return user_input
    try:
        return int(user_input)
    except ValueError:
        try:
            chat = await client.get_chat(user_input)
            return chat.id
        except Exception as e:
            logger.error(f"Không thể lấy ID cho '{user_input}': {e}")
            return None

async def update_last_processed_message_id(source_chat_id, target_chat_id, message_id):
    forward_rules_collection.update_one(
        {"source_chat_id": source_chat_id, "destination_chat_id": target_chat_id},
        {"$set": {"last_processed_message_id": message_id}},
        upsert=False
    )
    logger.debug(f"Đã cập nhật last_processed_message_id cho {source_chat_id} -> {target_chat_id} lên {message_id}")

# --- Hàm chính để forward tin nhắn ---
async def process_and_forward_message(client_used, message, rule):
    source_chat_id = rule["source_chat_id"]
    dest_chat_id = rule["destination_chat_id"]

    if not message.video:
        logger.debug(f"Tin nhắn ID {message.id} từ {source_chat_id} không phải là video. Bỏ qua.")
        return False

    try:
        await message.copy(chat_id=dest_chat_id, caption="", disable_notification=True)
        logger.info(f"Đã forward video (ID: {message.id}) từ {source_chat_id} đến {dest_chat_id}")
        return True
    except FloodWait as e:
        logger.warning(f"FloodWait: Chờ {e.value} giây.")
        await asyncio.sleep(e.value + 1)
        return await process_and_forward_message(client_used, message, rule)
    except (PeerIdInvalid, UserNotParticipant):
        logger.error(f"Lỗi: Không tìm thấy nhóm đích {dest_chat_id} hoặc bot/user không có quyền truy cập/thành viên.")
        return False
    except SessionExpired:
        logger.error(f"Session của client {client_used.name} đã hết hạn. Vui lòng đăng nhập lại.")
        return False
    except Exception as e:
        logger.error(f"Lỗi không xác định khi forward video (ID: {message.id}) đến {dest_chat_id}: {e}", exc_info=True)
        return False

# --- Hàm xử lý tin nhắn mới (real-time) ---
@bot_client.on_message(filters.video & filters.group)
@user_client.on_message(filters.video & filters.group)
async def handle_realtime_video_message(client, message):
    source_chat_id = message.chat.id
    rules_for_source = forward_rules_collection.find({"source_chat_id": source_chat_id})
    for rule in rules_for_source:
        task_key = (rule["source_chat_id"], rule["destination_chat_id"])
        if task_key in scanning_tasks and not scanning_tasks[task_key].done():
            logger.debug(f"Tin nhắn từ {source_chat_id} đang được xử lý bởi tác vụ scan. Bỏ qua realtime.")
            continue
        last_id_in_db = rule.get("last_processed_message_id", 0)
        if message.id > last_id_in_db:
            if await process_and_forward_message(client, message, rule):
                await update_last_processed_message_id(source_chat_id, rule["destination_chat_id"], message.id)

# --- Lệnh Telegram ---
@bot_client.on_message(filters.command("login") & filters.private)
async def login_command(client, message):
    if message.from_user.id not in config.ADMIN_USER_IDS:
        await message.reply_text("Lệnh này chỉ dành cho quản trị viên.")
        return
    if await user_client.is_connected:
        await message.reply_text("User session đã được đăng nhập rồi.")
        return
    try:
        await message.reply_text("Đang khởi động user session...\nVui lòng trả lời các tin nhắn tiếp theo để hoàn tất đăng nhập.")
        await user_client.start()
        me = await user_client.get_me()
        await message.reply_text(f"Đăng nhập user session thành công!\nXin chào, {me.first_name} (`{me.id}`).")
    except Exception as e:
        await message.reply_text(f"Lỗi khi cố gắng đăng nhập user session: {e}")
        logger.error(f"Lỗi khi đăng nhập user session: {e}", exc_info=True)

@bot_client.on_message(filters.command("set") & filters.private)
@admin_only
async def set_command(client, message):
    args = message.command
    if len(args) != 3:
        await message.reply_text("Cú pháp: `/set [source_id/username] [target_id/username]`")
        return
    source_input, target_input = args[1], args[2]
    client_to_resolve = user_client if await user_client.is_connected else bot_client
    if not await client_to_resolve.is_connected:
        await message.reply_text("Không có client nào được kết nối. Vui lòng `/login` user session trước.")
        return
    resolved_source_id = await get_chat_id_from_input(client_to_resolve, source_input)
    resolved_target_id = await get_chat_id_from_input(client_to_resolve, target_input)
    if not resolved_source_id:
        await message.reply_text(f"Không thể giải quyết ID cho nguồn: `{source_input}`.")
        return
    if not resolved_target_id:
        await message.reply_text(f"Không thể giải quyết ID cho đích: `{target_input}`.")
        return
    try:
        if forward_rules_collection.find_one({"source_chat_id": resolved_source_id, "destination_chat_id": resolved_target_id}):
            await message.reply_text(f"Quy tắc forward từ `{resolved_source_id}` đến `{resolved_target_id}` đã tồn tại.")
        else:
            new_rule = {"source_chat_id": resolved_source_id, "destination_chat_id": resolved_target_id, "last_processed_message_id": 0}
            forward_rules_collection.insert_one(new_rule)
            await message.reply_text(f"Đã thêm quy tắc:\nNguồn: `{resolved_source_id}`\nĐích: `{resolved_target_id}`.")
        logger.info(f"Lệnh /set: {resolved_source_id} -> {resolved_target_id} bởi admin {message.from_user.id}.")
    except Exception as e:
        await message.reply_text(f"Lỗi khi thiết lập quy tắc: {e}")
        logger.error(f"Lỗi khi thiết lập quy tắc: {e}", exc_info=True)

async def scan_rule_task(source_id, target_id, start_from_id):
    logger.info(f"Bắt đầu quét từ {source_id} -> {target_id} từ ID {start_from_id}")
    client_to_use = user_client if await user_client.is_connected else bot_client
    if not await client_to_use.is_connected:
        logger.error(f"Không có client nào kết nối để quét {source_id}.")
        return
    try:
        current_offset_id = start_from_id
        while True:
            messages_in_batch = [msg async for msg in client_to_use.get_chat_history(source_id, offset_id=current_offset_id, limit=100)]
            if not messages_in_batch:
                logger.info(f"Không tìm thấy tin nhắn mới nào từ {source_id} sau ID {current_offset_id}. Hoàn thành.")
                break
            last_message_id_in_batch = messages_in_batch[-1].id
            for msg in messages_in_batch:
                if await process_and_forward_message(client_to_use, msg, {"source_chat_id": source_id, "destination_chat_id": target_id}):
                    await update_last_processed_message_id(source_id, target_id, msg.id)
                await asyncio.sleep(0.1)
            current_offset_id = last_message_id_in_batch
            await asyncio.sleep(1)
        logger.info(f"Quét hoàn tất cho {source_id} -> {target_id}.")
    except ChannelInvalid:
        logger.error(f"Kênh nguồn {source_id} không hợp lệ. Dừng quét.")
    except Exception as e:
        logger.error(f"Lỗi khi quét {source_id} -> {target_id}: {e}", exc_info=True)
    finally:
        if (source_id, target_id) in scanning_tasks:
            del scanning_tasks[(source_id, target_id)]

@bot_client.on_message(filters.command("scan") & filters.private)
@admin_only
async def scan_command(client, message):
    await message.reply_text("Bắt đầu quét cho tất cả các quy tắc...")
    logger.info(f"Lệnh /scan bởi admin {message.from_user.id}.")
    rules = list(forward_rules_collection.find({}))
    if not rules:
        await message.reply_text("Không có quy tắc nào được cấu hình. Dùng /set trước.")
        return
    for rule in rules:
        source_id, target_id = rule["source_chat_id"], rule["destination_chat_id"]
        last_id = rule.get("last_processed_message_id", 0)
        task_key = (source_id, target_id)
        if task_key in scanning_tasks and not scanning_tasks[task_key].done():
            await message.reply_text(f"Quá trình scan cho `{source_id}` -> `{target_id}` đã đang chạy.")
            continue
        task = asyncio.create_task(scan_rule_task(source_id, target_id, last_id))
        scanning_tasks[task_key] = task
        await message.reply_text(f"Đã bắt đầu tác vụ quét cho `{source_id}` -> `{target_id}`.")

@bot_client.on_message(filters.command("stop") & filters.private)
@admin_only
async def stop_command(client, message):
    if not scanning_tasks:
        await message.reply_text("Không có quá trình quét nào đang chạy.")
        return
    stopped_count = 0
    for task_key, task in list(scanning_tasks.items()):
        if not task.done():
            task.cancel()
            stopped_count += 1
            logger.info(f"Đã hủy tác vụ scan cho {task_key} bởi admin {message.from_user.id}.")
    scanning_tasks.clear()
    if stopped_count > 0:
        await message.reply_text(f"Đã yêu cầu dừng {stopped_count} quá trình quét.")
    else:
        await message.reply_text("Không có quá trình quét nào đang hoạt động để dừng.")

# --- CẬP NHẬT DEBUG ---
@bot_client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_help_command(client, message):
    """Hiển thị thông tin trợ giúp."""
    # Dòng log để kiểm tra xem hàm có được gọi không
    logger.info(f"DEBUG: Lệnh '/{message.command[0]}' được nhận từ user ID: {message.from_user.id}")

    # Kiểm tra xem ID người dùng có trong danh sách admin không
    if message.from_user.id not in config.ADMIN_USER_IDS:
        # Dòng log nếu người dùng không phải admin
        logger.warning(f"DEBUG: User ID {message.from_user.id} không có trong danh sách admin: {config.ADMIN_USER_IDS}")
        await message.reply_text("Đây là bot forward tin nhắn riêng tư. Vui lòng liên hệ quản trị viên.")
        return
    
    # Nếu là admin, bot sẽ trả lời
    logger.info(f"DEBUG: User ID {message.from_user.id} là admin. Đang gửi tin nhắn trợ giúp.")
    await message.reply_text(
        "**Chào mừng Admin!**\n\n"
        "Đây là các lệnh bạn có thể sử dụng:\n"
        "`/login` - Đăng nhập user session để truy cập kênh/nhóm riêng tư.\n"
        "`/set [nguồn] [đích]` - Thiết lập quy tắc forward.\n"
        "`/scan` - Bắt đầu quét lại lịch sử theo quy tắc.\n"
        "`/stop` - Dừng tất cả các tác vụ quét đang chạy."
    )

async def main():
    logger.info("Đang khởi động các client...")
    await bot_client.start()
    logger.info("Bot client đã khởi động.")
    if await user_session_storage.get_auth_key():
        try:
            await user_client.start()
            me = await user_client.get_me()
            logger.info(f"User client đã tự động kết nối với session của {me.first_name} ({me.id}).")
        except Exception as e:
            logger.error(f"Không thể tự động kết nối user client: {e}")
    logger.info("Bot đang chạy... Nhấn CTRL+C để dừng.")
    await idle()
    logger.info("Bot đang dừng...")
    for task in scanning_tasks.values():
        task.cancel()
    await bot_client.stop()
    if await user_client.is_connected:
        await user_client.stop()
    if mongo_client:
        mongo_client.close()
        logger.info("Đã đóng kết nối MongoDB.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Phát hiện KeyboardInterrupt. Đang tắt bot.")
