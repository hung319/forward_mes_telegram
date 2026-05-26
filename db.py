import json
import aiosqlite
import config

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(config.SQLITE_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables()
    return _db


async def _init_tables():
    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            session_string TEXT,
            default_min_duration INTEGER DEFAULT 0,
            default_max_duration INTEGER
        );

        CREATE TABLE IF NOT EXISTS targets (
            user_id INTEGER NOT NULL,
            target_chat_id INTEGER NOT NULL,
            name TEXT,
            enabled INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, target_chat_id)
        );

        CREATE TABLE IF NOT EXISTS sources (
            user_id INTEGER NOT NULL,
            source_chat_id INTEGER NOT NULL,
            target_chat_id INTEGER NOT NULL,
            enabled INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, source_chat_id)
        );

        CREATE TABLE IF NOT EXISTS filters (
            user_id INTEGER NOT NULL,
            source_chat_id INTEGER NOT NULL,
            media_types TEXT DEFAULT '["all"]',
            min_duration INTEGER DEFAULT 0,
            max_duration INTEGER,
            dc_ids TEXT DEFAULT '[]',
            enabled INTEGER DEFAULT 1,
            remove_caption INTEGER DEFAULT 0,
            remove_forward_header INTEGER DEFAULT 0,
            min_file_size INTEGER DEFAULT 0,
            max_file_size INTEGER,
            require_caption INTEGER DEFAULT 0,
            require_hashtags INTEGER DEFAULT 0,
            block_list TEXT DEFAULT '[]',
            only_from_users TEXT DEFAULT '[]',
            block_from_users TEXT DEFAULT '[]',
            PRIMARY KEY (user_id, source_chat_id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS forwarded_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source INTEGER NOT NULL,
            target INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            forwarded_at TEXT,
            media_type TEXT,
            synced_at TEXT,
            UNIQUE(user_id, source, target, message_id)
        );
    """)
    await _db.commit()


def row_to_dict(row: aiosqlite.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: list[aiosqlite.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# ─── Users ──────────────────────────────────────────────────────


async def get_user(user_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return row_to_dict(await cursor.fetchone())


async def upsert_user(user_id: int, **fields):
    """Set fields on a user row. Creates if not exists."""
    db = await get_db()
    existing = await get_user(user_id)
    if existing:
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [user_id]
        await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
    else:
        keys = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        vals = list(fields.values())
        await db.execute(
            f"INSERT INTO users (user_id, {keys}) VALUES (?, {placeholders})",
            [user_id] + vals,
        )
    await db.commit()


# ─── Settings ────────────────────────────────────────────────────


async def get_setting(key: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM settings WHERE key = ?", (key,))
    return row_to_dict(await cursor.fetchone())


async def upsert_setting(key: str, **fields):
    db = await get_db()
    existing = await get_setting(key)
    if existing:
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [key]
        await db.execute(f"UPDATE settings SET {sets} WHERE key = ?", vals)
    else:
        keys = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        vals = list(fields.values())
        await db.execute(
            f"INSERT INTO settings (key, {keys}) VALUES (?, {placeholders})",
            [key] + vals,
        )
    await db.commit()


# ─── Forwarded Messages ─────────────────────────────────────────


async def get_forwarded_message(user_id: int, source: int, target: int, message_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM forwarded_messages
           WHERE user_id = ? AND source = ? AND target = ? AND message_id = ?""",
        (user_id, source, target, message_id),
    )
    return row_to_dict(await cursor.fetchone())


async def upsert_forwarded_message(user_id: int, source: int, target: int, message_id: int, **fields):
    db = await get_db()
    await db.execute(
        """INSERT INTO forwarded_messages (user_id, source, target, message_id, forwarded_at, media_type, synced_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id, source, target, message_id)
           DO UPDATE SET forwarded_at = excluded.forwarded_at,
                         media_type = excluded.media_type,
                         synced_at = excluded.synced_at""",
        (
            user_id,
            source,
            target,
            message_id,
            fields.get("forwarded_at"),
            fields.get("media_type"),
            fields.get("synced_at"),
        ),
    )
    await db.commit()


async def count_forwarded_messages(user_id: int) -> int:
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM forwarded_messages WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


async def get_forwarded_message_ids(user_id: int, source: int = None, target: int = None) -> set:
    db = await get_db()
    query = "SELECT message_id FROM forwarded_messages WHERE user_id = ?"
    params = [user_id]
    if source is not None:
        query += " AND source = ?"
        params.append(source)
    if target is not None:
        query += " AND target = ?"
        params.append(target)
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return {r["message_id"] for r in rows}


async def get_all_forwarded_messages(user_id: int) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM forwarded_messages WHERE user_id = ?", (user_id,)
    )
    return rows_to_list(await cursor.fetchall())
