from pymongo import MongoClient
import config
from enum import Enum

mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.DATABASE_NAME]
filters_collection = db["filters"]
targets_collection = db["targets"]
sources_collection = db["sources"]


class MediaType(Enum):
    VIDEO = "video"
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIO = "audio"
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
    ):
        self.user_id = user_id
        self.source_chat_id = source_chat_id
        self.media_types = media_types or [MediaType.ALL]
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.dc_ids = dc_ids or []
        self.enabled = enabled

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "source_chat_id": self.source_chat_id,
            "media_types": [m.value for m in self.media_types],
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "dc_ids": self.dc_ids,
            "enabled": self.enabled,
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
        )

    def save(self):
        filters_collection.update_one(
            {"user_id": self.user_id, "source_chat_id": self.source_chat_id},
            {"$set": self.to_dict()},
            upsert=True,
        )

    @staticmethod
    def get(user_id: int, source_chat_id: int) -> "FilterConfig":
        data = filters_collection.find_one(
            {"user_id": user_id, "source_chat_id": source_chat_id}
        )
        if data:
            return FilterConfig.from_dict(data)
        return FilterConfig(user_id=user_id, source_chat_id=source_chat_id)

    @staticmethod
    def get_all(user_id: int) -> list:
        cursor = filters_collection.find({"user_id": user_id})
        return [FilterConfig.from_dict(doc) for doc in cursor]

    def matches(self, message) -> bool:
        if not self.enabled:
            return False

        media_type = self._get_media_type(message)
        if MediaType.ALL not in self.media_types:
            if media_type not in self.media_types:
                return False

        if media_type == MediaType.VIDEO:
            if message.video and message.video.duration:
                if message.video.duration < self.min_duration:
                    return False
                if self.max_duration and message.video.duration > self.max_duration:
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

    def save(self):
        targets_collection.update_one(
            {"user_id": self.user_id, "target_chat_id": self.target_chat_id},
            {"$set": self.to_dict()},
            upsert=True,
        )

    @staticmethod
    def get(user_id: int, target_chat_id: int):
        data = targets_collection.find_one(
            {"user_id": user_id, "target_chat_id": target_chat_id}
        )
        if data:
            return TargetConfig.from_dict(data)
        return None

    @staticmethod
    def get_all(user_id: int) -> list:
        cursor = targets_collection.find({"user_id": user_id})
        return [TargetConfig.from_dict(doc) for doc in cursor]

    @staticmethod
    def delete(user_id: int, target_chat_id: int):
        # Delete all sources under this target
        sources_collection.delete_many(
            {"user_id": user_id, "target_chat_id": target_chat_id}
        )
        # Delete target
        targets_collection.delete_one(
            {"user_id": user_id, "target_chat_id": target_chat_id}
        )

    def get_sources(self) -> list:
        """Get all sources for this target"""
        cursor = sources_collection.find(
            {"user_id": self.user_id, "target_chat_id": self.target_chat_id}
        )
        return [SourceConfig.from_dict(doc) for doc in cursor]


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

    def save(self):
        sources_collection.update_one(
            {"user_id": self.user_id, "source_chat_id": self.source_chat_id},
            {"$set": self.to_dict()},
            upsert=True,
        )

    @staticmethod
    def get(user_id: int, source_chat_id: int) -> "SourceConfig":
        data = sources_collection.find_one(
            {"user_id": user_id, "source_chat_id": source_chat_id}
        )
        if data:
            return SourceConfig.from_dict(data)
        return None

    @staticmethod
    def get_all(user_id: int) -> list:
        cursor = sources_collection.find({"user_id": user_id})
        return [SourceConfig.from_dict(doc) for doc in cursor]

    @staticmethod
    def get_by_target(user_id: int, target_chat_id: int) -> list:
        """Get all sources for a specific target"""
        cursor = sources_collection.find(
            {"user_id": user_id, "target_chat_id": target_chat_id}
        )
        return [SourceConfig.from_dict(doc) for doc in cursor]

    @staticmethod
    def delete(user_id: int, source_chat_id: int):
        sources_collection.delete_one(
            {"user_id": user_id, "source_chat_id": source_chat_id}
        )
        filters_collection.delete_one(
            {"user_id": user_id, "source_chat_id": source_chat_id}
        )
