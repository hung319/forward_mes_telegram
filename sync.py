import asyncio
from datetime import datetime
from logger import get_unsynced_messages, mark_synced, cleanup_synced_messages
import config
import db as db_module


async def sync_to_database():
    """Background task: sync logged messages to database"""
    while True:
        try:
            unsynced = await get_unsynced_messages()

            if unsynced:
                for entry in unsynced:
                    await db_module.upsert_forwarded_message(
                        user_id=entry["user_id"],
                        source=entry["source"],
                        target=entry["target"],
                        message_id=entry["message_id"],
                        forwarded_at=entry["timestamp"],
                        media_type=entry.get("media_type"),
                        synced_at=datetime.now().isoformat(),
                    )

                message_ids = [e["message_id"] for e in unsynced]
                await mark_synced(message_ids)
                print(f"✅ Synced {len(message_ids)} messages to database")

            # Cleanup old synced messages
            await cleanup_synced_messages()

        except Exception as e:
            print(f"❌ Sync error: {e}")

        await asyncio.sleep(config.SYNC_INTERVAL)


def start_sync_task():
    """Start the sync background task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_to_database())


async def get_forwarded_message_ids(
    user_id: int, source: int = None, target: int = None
) -> set:
    """Get forwarded message IDs for a user/source/target"""
    return await db_module.get_forwarded_message_ids(user_id, source, target)


async def is_message_forwarded(
    user_id: int, source: int, target: int, message_id: int
) -> bool:
    """Check if a message was already forwarded"""
    return (
        await db_module.get_forwarded_message(user_id, source, target, message_id)
    ) is not None
