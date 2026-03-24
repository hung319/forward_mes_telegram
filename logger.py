import os
import json
import asyncio
import aiofiles
from datetime import datetime
from pathlib import Path

LOG_FILE = os.getenv("LOG_FILE", "message_ids.log")
LOG_LOCK = asyncio.Lock()


async def log_message(
    user_id: int,
    source_chat_id: int,
    target_chat_id: int,
    message_id: int,
    media_type: str = None,
):
    """Log message ID to file (async)"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "source": source_chat_id,
        "target": target_chat_id,
        "message_id": message_id,
        "media_type": media_type,
        "synced": False,
    }

    async with LOG_LOCK:
        async with aiofiles.open(LOG_FILE, "a") as f:
            await f.write(json.dumps(entry) + "\n")


async def get_unsynced_messages() -> list:
    """Get all unsynced messages from log file"""
    unsynced = []
    if not os.path.exists(LOG_FILE):
        return unsynced

    async with LOG_LOCK:
        async with aiofiles.open(LOG_FILE, "r") as f:
            async for line in f:
                try:
                    entry = json.loads(line.strip())
                    if not entry.get("synced", False):
                        unsynced.append(entry)
                except json.JSONDecodeError:
                    continue
    return unsynced


async def mark_synced(message_ids: list):
    """Mark messages as synced in log file"""
    if not message_ids:
        return

    temp_file = LOG_FILE + ".tmp"

    async with LOG_LOCK:
        # Read all entries
        all_entries = []
        if os.path.exists(LOG_FILE):
            async with aiofiles.open(LOG_FILE, "r") as f:
                async for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("message_id") in message_ids:
                            entry["synced"] = True
                            entry["synced_at"] = datetime.now().isoformat()
                        all_entries.append(entry)
                    except json.JSONDecodeError:
                        continue

        # Write back
        async with aiofiles.open(temp_file, "w") as f:
            for entry in all_entries:
                await f.write(json.dumps(entry) + "\n")

        os.replace(temp_file, LOG_FILE)


async def cleanup_synced_messages():
    """Remove synced messages older than 7 days"""
    if not os.path.exists(LOG_FILE):
        return

    temp_file = LOG_FILE + ".tmp"
    cutoff = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7 days

    async with LOG_LOCK:
        async with aiofiles.open(LOG_FILE, "r") as f:
            async with aiofiles.open(temp_file, "w") as out:
                async for line in f:
                    try:
                        entry = json.loads(line.strip())
                        # Keep if not synced OR recently synced (within 24h)
                        if not entry.get("synced"):
                            await out.write(line)
                        else:
                            # Check if synced within 24h
                            if entry.get("synced_at"):
                                synced_time = datetime.fromisoformat(
                                    entry["synced_at"]
                                ).timestamp()
                                if datetime.now().timestamp() - synced_time < 86400:
                                    await out.write(line)
                    except json.JSONDecodeError:
                        continue

        os.replace(temp_file, LOG_FILE)


async def get_all_forwarded_ids(user_id: int = None) -> dict:
    """Get all forwarded message IDs (from database)"""
    # This will be called from main bot to get DB data
    pass
