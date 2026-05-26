import json
from enum import Enum
import db as db_module


class MediaType(Enum):
    VIDEO = "video"
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"  # Voice message
    VIDEO_NOTE = "video_note"  # Video note (circle)
    STICKER = "sticker"
    ANIMATION = "animation"  # GIF
    TEXT = "text"
    ALL = "all"


class FilterConfig:
    """Filter configuration for a source chat"""

    def __init__(
        self,
        user_id: int,
        source_chat_id: int,
        media_types: list = None,
        min_duration: int = 0,
        max_duration: int = None,
        dc_ids: list = None,
        enabled: bool = True,
        # Forward options
        remove_caption: bool = False,
        remove_forward_header: bool = False,
        # Size filters
        min_file_size: int = 0,  # in bytes
        max_file_size: int = None,
        # Content filters
        require_caption: bool = False,
        require_hashtags: bool = False,
        block_list: list = None,  # Block words
        # Advanced
        only_from_users: list = None,  # Only from specific users
        block_from_users: list = None,  # Block from specific users
    ):
        self.user_id = user_id
        self.source_chat_id = source_chat_id
        self.media_types = media_types or [MediaType.ALL]
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.dc_ids = dc_ids or []
        self.enabled = enabled
        # Forward options
        self.remove_caption = remove_caption
        self.remove_forward_header = remove_forward_header
        # Size filters
        self.min_file_size = min_file_size
        self.max_file_size = max_file_size
        # Content filters
        self.require_caption = require_caption
        self.require_hashtags = require_hashtags
        self.block_list = block_list or []
        # Advanced
        self.only_from_users = only_from_users or []
        self.block_from_users = block_from_users or []

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "source_chat_id": self.source_chat_id,
            "media_types": [m.value for m in self.media_types],
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "dc_ids": self.dc_ids,
            "enabled": self.enabled,
            "remove_caption": self.remove_caption,
            "remove_forward_header": self.remove_forward_header,
            "min_file_size": self.min_file_size,
            "max_file_size": self.max_file_size,
            "require_caption": self.require_caption,
            "require_hashtags": self.require_hashtags,
            "block_list": self.block_list,
            "only_from_users": self.only_from_users,
            "block_from_users": self.block_from_users,
        }

    @staticmethod
    def from_dict(data: dict) -> "FilterConfig":
        return FilterConfig(
            user_id=data["user_id"],
            source_chat_id=data["source_chat_id"],
            media_types=[MediaType(m) for m in data.get("media_types", ["all"])],
            min_duration=data.get("min_duration", 0),
            max_duration=data.get("max_duration"),
            dc_ids=data.get("dc_ids", []),
            enabled=data.get("enabled", True),
            remove_caption=data.get("remove_caption", False),
            remove_forward_header=data.get("remove_forward_header", False),
            min_file_size=data.get("min_file_size", 0),
            max_file_size=data.get("max_file_size"),
            require_caption=data.get("require_caption", False),
            require_hashtags=data.get("require_hashtags", False),
            block_list=data.get("block_list", []),
            only_from_users=data.get("only_from_users", []),
            block_from_users=data.get("block_from_users", []),
        )

    async def save(self):
        d = self.to_dict()
        # Convert list fields to JSON strings for SQLite
        db = await db_module.get_db()
        await db.execute(
            """INSERT OR REPLACE INTO filters
               (user_id, source_chat_id, media_types, min_duration, max_duration,
                dc_ids, enabled, remove_caption, remove_forward_header,
                min_file_size, max_file_size, require_caption, require_hashtags,
                block_list, only_from_users, block_from_users)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                d["user_id"],
                d["source_chat_id"],
                json.dumps(d["media_types"]),
                d["min_duration"],
                d["max_duration"],
                json.dumps(d["dc_ids"]),
                1 if d["enabled"] else 0,
                1 if d["remove_caption"] else 0,
                1 if d["remove_forward_header"] else 0,
                d["min_file_size"],
                d["max_file_size"],
                1 if d["require_caption"] else 0,
                1 if d["require_hashtags"] else 0,
                json.dumps(d["block_list"]),
                json.dumps(d["only_from_users"]),
                json.dumps(d["block_from_users"]),
            ),
        )
        await db.commit()

    @staticmethod
    async def get(user_id: int, source_chat_id: int) -> "FilterConfig":
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM filters WHERE user_id = ? AND source_chat_id = ?",
            (user_id, source_chat_id),
        )
        row = await cursor.fetchone()
        if row:
            return FilterConfig.from_dict(_row_to_filter_dict(row))
        return FilterConfig(user_id=user_id, source_chat_id=source_chat_id)

    @staticmethod
    async def get_all(user_id: int) -> list:
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM filters WHERE user_id = ?", (user_id,)
        )
        rows = await cursor.fetchall()
        return [FilterConfig.from_dict(_row_to_filter_dict(r)) for r in rows]

    def matches(self, message) -> bool:
        if not self.enabled:
            return False

        media_type = self._get_media_type(message)

        # Check media type
        if MediaType.ALL not in self.media_types:
            if media_type not in self.media_types:
                return False

        # Check video duration
        if media_type == MediaType.VIDEO:
            if message.video and message.video.duration:
                if message.video.duration < self.min_duration:
                    return False
                if self.max_duration and message.video.duration > self.max_duration:
                    return False

        # Check file size
        if message.document or message.video or message.audio:
            file_size = (
                message.document.file_size
                or message.video.file_size
                or message.audio.file_size
                or 0
            )
            if file_size < self.min_file_size:
                return False
            if self.max_file_size and file_size > self.max_file_size:
                return False

        # Check require caption
        if self.require_caption:
            if not message.caption or not message.caption.text.strip():
                return False

        # Check require hashtags
        if self.require_hashtags:
            if not message.caption:
                return False
            text = message.caption.text or ""
            if "#" not in text:
                return False

        # Check block list
        if self.block_list and message.caption:
            text = message.caption.text or ""
            text_lower = text.lower()
            for blocked in self.block_list:
                if blocked.lower() in text_lower:
                    return False

        # Check user filters
        if message.from_user:
            user_id = message.from_user.id

            # Block from specific users
            if self.block_from_users and user_id in self.block_from_users:
                return False

            # Only from specific users
            if self.only_from_users and user_id not in self.only_from_users:
                return False

        return True

    def _get_media_type(self, message) -> MediaType:
        if message.video:
            return MediaType.VIDEO
        elif message.photo:
            return MediaType.PHOTO
        elif message.document:
            return MediaType.DOCUMENT
        elif message.audio:
            return MediaType.AUDIO
        elif message.voice:
            return MediaType.VOICE
        elif message.video_note:
            return MediaType.VIDEO_NOTE
        elif message.sticker:
            return MediaType.STICKER
        elif message.animation:
            return MediaType.ANIMATION
        else:
            return MediaType.TEXT


class TargetConfig:
    """Target configuration - can contain multiple sources"""

    def __init__(
        self,
        user_id: int,
        target_chat_id: int,
        name: str = None,
        enabled: bool = True,
    ):
        self.user_id = user_id
        self.target_chat_id = target_chat_id
        self.name = name or str(target_chat_id)
        self.enabled = enabled

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "target_chat_id": self.target_chat_id,
            "name": self.name,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(data: dict) -> "TargetConfig":
        return TargetConfig(
            user_id=data["user_id"],
            target_chat_id=data["target_chat_id"],
            name=data.get("name"),
            enabled=data.get("enabled", True),
        )

    async def save(self):
        db = await db_module.get_db()
        await db.execute(
            """INSERT OR REPLACE INTO targets (user_id, target_chat_id, name, enabled)
               VALUES (?, ?, ?, ?)""",
            (self.user_id, self.target_chat_id, self.name, 1 if self.enabled else 0),
        )
        await db.commit()

    @staticmethod
    async def get(user_id: int, target_chat_id: int):
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM targets WHERE user_id = ? AND target_chat_id = ?",
            (user_id, target_chat_id),
        )
        row = await cursor.fetchone()
        if row:
            return TargetConfig.from_dict(dict(row))
        return None

    @staticmethod
    async def get_all(user_id: int) -> list:
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM targets WHERE user_id = ?", (user_id,)
        )
        rows = await cursor.fetchall()
        return [TargetConfig.from_dict(dict(r)) for r in rows]

    @staticmethod
    async def delete(user_id: int, target_chat_id: int):
        db = await db_module.get_db()
        await db.execute(
            "DELETE FROM sources WHERE user_id = ? AND target_chat_id = ?",
            (user_id, target_chat_id),
        )
        await db.execute(
            "DELETE FROM targets WHERE user_id = ? AND target_chat_id = ?",
            (user_id, target_chat_id),
        )
        await db.commit()

    async def get_sources(self) -> list:
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM sources WHERE user_id = ? AND target_chat_id = ?",
            (self.user_id, self.target_chat_id),
        )
        rows = await cursor.fetchall()
        return [SourceConfig.from_dict(dict(r)) for r in rows]


class SourceConfig:
    """Configuration for a source chat"""

    def __init__(
        self,
        user_id: int,
        source_chat_id: int,
        target_chat_id: int,
        enabled: bool = True,
    ):
        self.user_id = user_id
        self.source_chat_id = source_chat_id
        self.target_chat_id = target_chat_id
        self.enabled = enabled

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "source_chat_id": self.source_chat_id,
            "target_chat_id": self.target_chat_id,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(data: dict) -> "SourceConfig":
        return SourceConfig(
            user_id=data["user_id"],
            source_chat_id=data["source_chat_id"],
            target_chat_id=data["target_chat_id"],
            enabled=data.get("enabled", True),
        )

    async def save(self):
        db = await db_module.get_db()
        await db.execute(
            """INSERT OR REPLACE INTO sources (user_id, source_chat_id, target_chat_id, enabled)
               VALUES (?, ?, ?, ?)""",
            (self.user_id, self.source_chat_id, self.target_chat_id, 1 if self.enabled else 0),
        )
        await db.commit()

    @staticmethod
    async def get(user_id: int, source_chat_id: int) -> "SourceConfig":
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM sources WHERE user_id = ? AND source_chat_id = ?",
            (user_id, source_chat_id),
        )
        row = await cursor.fetchone()
        if row:
            return SourceConfig.from_dict(dict(row))
        return None

    @staticmethod
    async def get_all(user_id: int) -> list:
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM sources WHERE user_id = ?", (user_id,)
        )
        rows = await cursor.fetchall()
        return [SourceConfig.from_dict(dict(r)) for r in rows]

    @staticmethod
    async def get_by_target(user_id: int, target_chat_id: int) -> list:
        db = await db_module.get_db()
        cursor = await db.execute(
            "SELECT * FROM sources WHERE user_id = ? AND target_chat_id = ?",
            (user_id, target_chat_id),
        )
        rows = await cursor.fetchall()
        return [SourceConfig.from_dict(dict(r)) for r in rows]

    @staticmethod
    async def delete(user_id: int, source_chat_id: int):
        db = await db_module.get_db()
        await db.execute(
            "DELETE FROM sources WHERE user_id = ? AND source_chat_id = ?",
            (user_id, source_chat_id),
        )
        await db.execute(
            "DELETE FROM filters WHERE user_id = ? AND source_chat_id = ?",
            (user_id, source_chat_id),
        )
        await db.commit()


# ─── Helpers ─────────────────────────────────────────────────────


def _row_to_filter_dict(row) -> dict:
    """Convert a sqlite Row to a dict with JSON fields decoded."""
    d = dict(row)
    # Decode JSON string fields
    for field in ("media_types", "dc_ids", "block_list", "only_from_users", "block_from_users"):
        if isinstance(d.get(field), str):
            d[field] = json.loads(d[field])
    # Convert integer booleans back
    for field in ("enabled", "remove_caption", "remove_forward_header",
                  "require_caption", "require_hashtags"):
        if field in d:
            d[field] = bool(d[field])
    return d


def format_file_size(bytes_size: int) -> str:
    """Format bytes to human readable size"""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f}KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f}MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f}GB"


# Presets
DURATION_PRESETS = {
    "0": "Any",
    "10": "10s+",
    "30": "30s+",
    "60": "1m+",
    "120": "2m+",
    "180": "3m+",
    "300": "5m+",
    "600": "10m+",
}

FILE_SIZE_PRESETS = {
    "0": "Any",
    "1048576": "1MB+",
    "5242880": "5MB+",
    "10485760": "10MB+",
    "20971520": "20MB+",
    "52428800": "50MB+",
}
