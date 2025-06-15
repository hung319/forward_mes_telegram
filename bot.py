import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
import config

mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.DATABASE_NAME]
users = db["users"]
forwards = db["forwards"]
settings = db["settings"]

bot = Client("forward_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

ADMIN_IDS = config.ADMIN_IDS
scanning = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_adminonly():
    setting = settings.find_one({"_id": "adminonly"})
    return setting and setting.get("enabled", False)

async def ensure_peer(client, chat_id):
    try:
        return await client.resolve_peer(chat_id)
    except Exception as e:
        print(f"[DEBUG] ensure_peer error with chat_id {chat_id}: {e}")
        return None

@bot.on_message(filters.command("set"))
async def set_forward(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        source = int(message.command[1])
        target = int(message.command[2])
        last_id = int(message.command[3]) if len(message.command) > 3 else 0
    except (IndexError, ValueError):
        return await message.reply("❗ Dùng: /set [source_chat_id] [target_chat_id] [id_last_chat]")

    forwards.update_one(
        {"user_id": message.from_user.id, "source": source, "target": target},
        {"$set": {"last_message_id": last_id}},
        upsert=True
    )

    await message.reply(f"✅ Đã thêm cấu hình từ `{source}` ➔ `{target}` với ID `{last_id}`")

@bot.on_message(filters.command("list"))
async def list_forward(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    data = forwards.find({"user_id": message.from_user.id})
    text = "📋 **Danh sách forward:**\n"
    for item in data:
        text += f"- `{item['source']}` ➔ `{item['target']}` (Last ID: `{item.get('last_message_id', 0)}`)\n"
    await message.reply(text or "📋 Danh sách trống.")

@bot.on_message(filters.command("unset"))
async def unset_forward(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    try:
        source = int(message.command[1])
        target = int(message.command[2])
    except (IndexError, ValueError):
        return await message.reply("❗ Dùng: /unset [source_chat_id] [target_chat_id]")

    result = forwards.delete_one({"user_id": message.from_user.id, "source": source, "target": target})
    if result.deleted_count == 0:
        return await message.reply("❗ Cấu hình không tồn tại.")
    
    await message.reply("✅ Đã xóa cấu hình.")

@bot.on_message(filters.command("scan"))
async def start_scan(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    if scanning.get(message.from_user.id):
        return await message.reply("⚠️ Scan đang chạy.")

    user_data = users.find_one({"user_id": message.from_user.id})
    if not user_data or not user_data.get("session_string"):
        return await message.reply("❗ Vui lòng dùng /login [session_string] trước.")

    session_string = user_data["session_string"]
    scanning[message.from_user.id] = True

    from pyrogram import Client as UserClient

    async with UserClient(
        name=f"forward_session_{message.from_user.id}",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=session_string,
        workdir="sessions"
    ) as user_client:

        await message.reply("✅ Đã kết nối user session thành công.")

        try:
            data = forwards.find({"user_id": message.from_user.id})
            for row in data:
                await ensure_peer(user_client, row['source'])
                await ensure_peer(user_client, row['target'])

                last_forwarded_id = row.get("last_message_id", 0)
                await message.reply(f"▶️ Bắt đầu scan `{row['source']}` ➔ `{row['target']}` từ ID `{last_forwarded_id}`")

                first_forwarded_id = None

                async for msg in user_client.get_chat_history(row['source']):
                    if not scanning.get(message.from_user.id):
                        return await message.reply("🛑 Đã dừng scan.")

                    if msg.id <= last_forwarded_id:
                        break

                    if msg.video:
                        try:
                            await user_client.copy_message(
                                chat_id=row['target'],
                                from_chat_id=row['source'],
                                message_id=msg.id,
                                caption="",
                                caption_entities=[]
                            )
                            if first_forwarded_id is None or msg.id > first_forwarded_id:
                                first_forwarded_id = msg.id
                        except Exception as e:
                            await message.reply(f"❌ Lỗi `{msg.id}` từ `{row['source']}` ➔ `{row['target']}`: {e}")

                if first_forwarded_id is not None:
                    forwards.update_one(
                        {"_id": row["_id"]},
                        {"$set": {"last_message_id": first_forwarded_id}}
                    )

                await message.reply(f"✅ Đã hoàn tất scan `{row['source']}` ➔ `{row['target']}` đến ID `{first_forwarded_id or last_forwarded_id}`")

            await message.reply("✅ Đã hoàn tất tất cả các scan.")
        finally:
            scanning[message.from_user.id] = False

@bot.on_message(filters.command("stop"))
async def stop_scan(client, message):
    if get_adminonly() and not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")
    
    scanning[message.from_user.id] = False
    await message.reply("🛑 Đã yêu cầu dừng scan.")

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
        upsert=True
    )

    await message.reply("✅ Đã lưu session thành công.")

@bot.on_message(filters.command("adminonly"))
async def toggle_adminonly(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ Bạn không có quyền.")

    current = get_adminonly()
    settings.update_one(
        {"_id": "adminonly"},
        {"$set": {"enabled": not current}},
        upsert=True
    )
    status = "✅ Đã bật chế độ chỉ admin." if not current else "❎ Đã tắt chế độ chỉ admin."
    await message.reply(status)

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply("🤖 Bot đã chạy thành công! Gõ /help để xem hướng dẫn.")

@bot.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = (
        "📜 **Hướng dẫn sử dụng bot**\n\n"
        "**/login [session_string]** - Lưu session Telegram để forward tin nhắn.\n"
        "**/set [source_chat_id] [target_chat_id] [id_last_chat]** - Thêm cấu hình forward từ nhóm nguồn ➔ nhóm đích.\n"
        "**/unset [source_chat_id] [target_chat_id]** - Xóa cấu hình forward.\n"
        "**/list** - Hiển thị danh sách forward hiện tại.\n"
        "**/scan** - Bắt đầu quét và forward video từ các nhóm đã cấu hình.\n"
        "**/stop** - Dừng quá trình scan hiện tại.\n"
        "**/adminonly** - Bật/tắt chế độ chỉ admin mới có thể sử dụng bot.\n"
        "**/help** - Hiển thị hướng dẫn này."
    )
    await message.reply(help_text)

print("🤖 Bot đã khởi động thành công!")
bot.run()
