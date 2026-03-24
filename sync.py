import asyncio
import os
from datetime import datetime
from logger import get_unsynced_messages, mark_synced, cleanup_synced_messages
from pymongo import MongoClient
import config

# Config from environment
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300))  # 5 minutes default

mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.DATABASE_NAME]
forwards = db["forwards"]
forwarded_messages = db["forwarded_messages"]


async def sync_to_database():
    """Background task: sync logged messages to database"""
    while True:
        try:
            unsynced = await get_unsynced_messages()

            if unsynced:
                message_ids = []
                for entry in unsynced:
                    # Store in database
                    forwarded_messages.update_one(
                        {
                            "user_id": entry["user_id"],
                            "source": entry["source"],
                            "target": entry["target"],
                            "message_id": entry["message_id"],
                        },
                        {
                            "$set": {
                                "forwarded_at": entry["timestamp"],
                                "media_type": entry.get("media_type"),
                                "synced_at": datetime.now().isoformat(),
                            }
                        },
                        upsert=True,
                    )
                    message_ids.append(entry["message_id"])

                # Mark as synced in log file
                await mark_synced(message_ids)
                print(f"✅ Synced {len(message_ids)} messages to database")

            # Cleanup old synced messages
            await cleanup_synced_messages()

        except Exception as e:
            print(f"❌ Sync error: {e}")

        await asyncio.sleep(SYNC_INTERVAL)


def start_sync_task():
    """Start the sync background task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_to_database())


async def get_forwarded_message_ids(
    user_id: int, source: int = None, target: int = None
) -> set:
    """Get forwarded message IDs for a user/source/target"""
    query = {"user_id": user_id}
    if source:
        query["source"] = source
    if target:
        query["target"] = target

    cursor = forwarded_messages.find(query, {"message_id": 1})
    return {doc["message_id"] for doc in cursor}


async def is_message_forwarded(
    user_id: int, source: int, target: int, message_id: int
) -> bool:
    """Check if a message was already forwarded"""
    return (
        forwarded_messages.find_one(
            {
                "user_id": user_id,
                "source": source,
                "target": target,
                "message_id": message_id,
            }
        )
        is not None
    )
