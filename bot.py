import os
import asyncio
import aiofiles
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from pymongo import MongoClient
import config

# Database setup
mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.DATABASE_NAME]
users = db["users"]
forwards_db = db["forwards"]
settings = db["settings"]

# Initialize bot
bot = Client(
    "forward_bot_realtime",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

ADMIN_IDS = config.ADMIN_IDS
user_clients = {}  # Store user client sessions
realtime_running = {}


def is_admin(user_id):
    return user_id in ADMIN_IDS


def get_adminonly():
    setting = settings.find_one({"_id": "adminonly"})
    return setting and setting.get("enabled", False)


# Import modules
from filters import FilterConfig, MediaType, SourceConfig, TargetConfig
from logger import log_message
from sync import is_message_forwarded, get_forwarded_message_ids
from menu import (
    build_main_menu_keyboard,
    build_filter_keyboard,
    handle_callback,
)

# ============ HELP COMMAND ============


@bot.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = """
📖 **Hướng dẫn sử dụng Bot**

**👤 Authentication:**
• `/login [session_string]` - Lưu session Telegram

**🎯 Target Management:**
• `/addtarget [target_id] [tên]` - Tạo target mới
• `/deletetarget [target_id]` - Xóa target
• `/targets` - Danh sách target

**📨 Source Management:**
• `/addsource [source_id]` - Thêm source vào target hiện tại
• `/removesource [source_id]` - Xóa source
• `/list` - Danh sách sources

**⚡ Realtime:**
• `/realtime on` - Bật realtime
• `/realtime off` - Tắt realtime

**⚙️ Filter:**
• `/config [source_id]` - Cấu hình filter
• `/default [min]_[max]` - Duration mặc định
• `/menu` - Menu inline

**📊 Stats:**
• `/stats` - Thống kê

**🔧 Admin:**
• `/adminonly` - Toggle admin only
"""
    await message.reply(help_text, parse_mode="markdown")


# ============ START COMMAND ============


@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply(
        "🤖 **Bot đã chạy!**\n\nGõ /help để xem hướng dẫn.",
        reply_markup=build_main_menu_keyboard(),
        parse_mode="markdown",
    )


# ============ LOGIN COMMAND ============


@bot.on_message(filters.command("login"))
async def login_session(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        session_string = message.command[1]
    except IndexError:
        return await message.reply("❗ Dùng: /login [session_string]")

    users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"session_string": session_string}},
        upsert=True,
    )

    await message.reply("✅ Đã lưu session thành công.")


# ============ ADD TARGET ============


@bot.on_message(filters.command("addtarget"))
async def add_target(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        target_id = int(message.command[1])
        name = " ".join(message.command[2:]) if len(message.command) > 2 else None
    except (IndexError, ValueError):
        return await message.reply(
            "❗ Dùng: /addtarget [target_id] [tên]\nVí dụ: /addtarget -100123456789"
        )

    target_config = TargetConfig(
        user_id=message.from_user.id,
        target_chat_id=target_id,
        name=name,
        enabled=True,
    )
    target_config.save()

    await message.reply(f"✅ Đã tạo target: `{target_id}` ({name or 'Default'})")


# ============ DELETE TARGET ============


@bot.on_message(filters.command("deletetarget"))
async def delete_target(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        target_id = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("❗ Dùng: /deletetarget [target_id]")

    TargetConfig.delete(message.from_user.id, target_id)
    await message.reply(f"✅ Đã xóa target `{target_id}` và tất cả sources")


# ============ LIST TARGETS ============


@bot.on_message(filters.command("targets"))
async def list_targets(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    targets = TargetConfig.get_all(message.from_user.id)

    if not targets:
        return await message.reply(
            "📂 Chưa có target nào.\n\nDùng /addtarget [target_id] để tạo."
        )

    text = "📂 **Danh sách Target:**\n\n"
    for target in targets:
        sources = target.get_sources()
        enabled = sum(1 for s in sources if s.enabled)
        status = "🟢" if target.enabled else "🔴"
        text += f"{status} `{target.target_chat_id}` - {target.name}\n"
        text += f"   └── {len(sources)} sources ({enabled} 🟢)\n\n"

    text += "Dùng /menu để quản lý qua inline keyboard"

    await message.reply(text, parse_mode="markdown")


# ============ ADD SOURCE ============


@bot.on_message(filters.command("addsource"))
async def add_source(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    # First, check if user has any targets
    targets = TargetConfig.get_all(message.from_user.id)
    if not targets:
        return await message.reply(
            "❗ Cần tạo target trước!\nDùng: /addtarget [target_id]"
        )

    try:
        source_id = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("❗ Dùng: /addsource [source_id]")

    # If multiple targets, ask which one to use
    if len(targets) == 1:
        target_id = targets[0].target_chat_id
    else:
        # Show list of targets for user to choose
        text = "Chọn target để thêm source:\n\n"
        for i, t in enumerate(targets):
            text += f"/selecttarget_{i} - {t.name or t.target_chat_id}\n"
        await message.reply(text)
        return

    source_config = SourceConfig(
        user_id=message.from_user.id,
        source_chat_id=source_id,
        target_chat_id=target_id,
        enabled=True,
    )
    source_config.save()

    # Create default filter
    filter_config = FilterConfig(
        user_id=message.from_user.id,
        source_chat_id=source_id,
        media_types=[MediaType.VIDEO],
        min_duration=60,
        enabled=True,
    )
    filter_config.save()

    await message.reply(f"✅ Đã thêm source: `{source_id}` ➔ `{target_id}`")


# ============ REMOVE SOURCE ============


@bot.on_message(filters.command("removesource"))
async def remove_source(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        source_id = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("❗ Dùng: /removesource [source_id]")

    SourceConfig.delete(message.from_user.id, source_id)
    await message.reply(f"✅ Đã xóa source `{source_id}`")


# ============ LIST SOURCES ============


@bot.on_message(filters.command("list"))
async def list_sources(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    targets = TargetConfig.get_all(message.from_user.id)

    if not targets:
        return await message.reply("📋 Chưa có target nào.")

    text = "📋 **Danh sách:**\n\n"
    for target in targets:
        sources = target.get_sources()
        text += f"📂 `{target.target_chat_id}` - {target.name}\n"
        for src in sources:
            status = "🟢" if src.enabled else "🔴"
            text += f"   {status} {src.source_chat_id}\n"
        text += "\n"

    await message.reply(text, parse_mode="markdown")


# ============ CONFIG COMMAND ============


@bot.on_message(filters.command("config"))
async def config_source(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        source_id = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("❗ Dùng: /config [source_id]")

    filter_config = FilterConfig.get(message.from_user.id, source_id)
    await message.reply(
        f"⚙️ **Cấu hình cho `{source_id}`:**\n\n"
        f"🟢 Enabled: {filter_config.enabled}\n"
        f"📹 Media: {[m.value for m in filter_config.media_types]}\n"
        f"⏱ Duration: {filter_config.min_duration}s - {filter_config.max_duration or '∞'}s\n"
        f"🔢 DC: {filter_config.dc_ids or 'All'}",
        reply_markup=build_filter_keyboard(message.from_user.id, source_id),
        parse_mode="markdown",
    )


# ============ MENU COMMAND ============


@bot.on_message(filters.command("menu"))
async def menu_command(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    await message.reply(
        "⚙️ **Menu cấu hình:**",
        reply_markup=build_main_menu_keyboard(),
        parse_mode="markdown",
    )


# ============ DEFAULT CONFIG ============


@bot.on_message(filters.command("default"))
async def default_config(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        parts = message.command[1].split("_")
        min_duration = int(parts[0]) if parts[0] else 0
        max_duration = int(parts[1]) if len(parts) > 1 and parts[1] else None
    except (IndexError, ValueError):
        return await message.reply(
            "❗ Dùng: /default [min_duration]_[max_duration]\nVí dụ: /default 60_300"
        )

    # Update default config for user
    users.update_one(
        {"user_id": message.from_user.id},
        {
            "$set": {
                "default_min_duration": min_duration,
                "default_max_duration": max_duration,
            }
        },
        upsert=True,
    )

    await message.reply(
        f"✅ Đã cập nhật default: {min_duration}s - {max_duration or '∞'}s"
    )


# ============ STATS COMMAND ============


@bot.on_message(filters.command("stats"))
async def stats_command(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    from sync import forwarded_messages
    from pymongo import DESCENDING

    total = forwarded_messages.count_documents({"user_id": message.from_user.id})

    # Count by media type
    media_stats = {}
    for doc in forwarded_messages.find({"user_id": message.from_user.id}):
        mt = doc.get("media_type", "unknown")
        media_stats[mt] = media_stats.get(mt, 0) + 1

    text = f"📊 **Thống kê:**\n\n"
    text += f"• Tổng tin nhắn đã forward: {total}\n\n"
    text += "Theo loại:\n"
    for mt, count in media_stats.items():
        text += f"  • {mt}: {count}\n"

    await message.reply(text, parse_mode="markdown")


# ============ REALTIME COMMAND ============


@bot.on_message(filters.command("realtime"))
async def toggle_realtime(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        action = message.command[1].lower()
    except IndexError:
        return await message.reply("❗ Dùng: /realtime on|off")

    user_id = message.from_user.id
    user_data = users.find_one({"user_id": user_id})

    if not user_data or not user_data.get("session_string"):
        return await message.reply("❗ Vui lòng /login [session_string] trước.")

    if action == "on":
        realtime_running[user_id] = True
        await message.reply("✅ Đã bật realtime forward!")

        # Start realtime forwarding in background
        asyncio.create_task(start_realtime_forward(user_id))

    elif action == "off":
        realtime_running[user_id] = False
        await message.reply("❎ Đã tắt realtime forward.")
    else:
        await message.reply("❗ Dùng: /realtime on|off")


# ============ REALTIME FORWARD TASK ============


async def forward_message(
    user_client, source_id: int, target_id: int, message, user_id: int
):
    """Forward a single message to target"""
    # Check if already forwarded
    if await is_message_forwarded(user_id, source_id, target_id, message.id):
        return False

    # Get filter config
    filter_config = FilterConfig.get(user_id, source_id)

    # Check if message matches filter
    if not filter_config.matches(message):
        return False

    try:
        await user_client.copy_message(
            chat_id=target_id, from_chat_id=source_id, message_id=message.id
        )

        # Log message ID to file
        media_type = None
        if message.video:
            media_type = "video"
        elif message.photo:
            media_type = "photo"
        elif message.document:
            media_type = "document"
        elif message.audio:
            media_type = "audio"

        await log_message(user_id, source_id, target_id, message.id, media_type)

        return True
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await forward_message(
            user_client, source_id, target_id, message, user_id
        )
    except Exception as e:
        print(f"Forward error: {e}")
        return False


async def realtime_message_handler(
    client, message, user_id: int, source_id: int, target_id: int
):
    """Handle incoming messages for realtime forwarding"""
    if not realtime_running.get(user_id, False):
        return

    await forward_message(client, source_id, target_id, message, user_id)


async def start_realtime_forward(user_id: int):
    """Background task for realtime message forwarding"""
    user_data = users.find_one({"user_id": user_id})
    session_string = user_data["session_string"]

    from pyrogram import Client as UserClient
    from pyrogram.types import Message

    # Track processed message IDs to avoid duplicates
    processed_ids = set()

    async with UserClient(
        name=f"realtime_{user_id}",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=session_string,
        workdir="sessions",
    ) as user_client:
        print(f"📡 Realtime forwarding started for user {user_id}")

        # Get sources
        sources = SourceConfig.get_all(user_id)
        source_targets = {
            src.source_chat_id: src.target_chat_id for src in sources if src.enabled
        }

        if not source_targets:
            print(f"⚠️ No enabled sources for user {user_id}")
            return

        # Listen to all chats (using iter_history for simplicity)
        async def check_new_messages():
            while realtime_running.get(user_id, False):
                for source_id, target_id in source_targets.items():
                    try:
                        async for msg in user_client.get_chat_history(
                            source_id, limit=10
                        ):
                            if msg.id not in processed_ids:
                                processed_ids.add(msg.id)
                                await forward_message(
                                    user_client, source_id, target_id, msg, user_id
                                )
                    except Exception as e:
                        print(f"Error checking {source_id}: {e}")

                await asyncio.sleep(3)  # Check every 3 seconds

        await check_new_messages()

        # Listen for new messages
        print(f"📡 Realtime forwarding started for user {user_id}")

        async for dialog in user_client.get_dialogs():
            source_config = SourceConfig.get(user_id, dialog.chat.id)
            if source_config and source_config.enabled:
                # Set up message handler for this chat
                pass


# ============ MESSAGE HANDLER (REALTIME) ============


@bot.on_message()
async def handle_incoming_message(client, message: Message):
    """Handle incoming messages in group chats"""
    # This would be triggered when bot is added to groups
    # Real-time forwarding logic would go here
    pass


# ============ CALLBACK QUERY HANDLER ============


@bot.on_callback_query()
async def handle_callback_query(client, callback_query):
    await handle_callback(client, callback_query)


# ============ ADMIN ONLY ============


@bot.on_message(filters.command("adminonly"))
async def toggle_adminonly(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    current = get_adminonly()
    settings.update_one(
        {"_id": "adminonly"}, {"$set": {"enabled": not current}}, upsert=True
    )
    status = (
        "✅ Đã bật chế độ chỉ admin." if not current else "❎ Đã tắt chế độ chỉ admin."
    )
    await message.reply(status)


# ============ START BOT ============

print("🤖 Bot đã khởi động!")
bot.run()
