"""Сервисы приложения."""

from .vk_api_service import VKAPIService
from .voice_service import VoiceService
from .long_poll_service import LongPollService
from .database_service import DatabaseService

__all__ = ["VKAPIService", "VoiceService", "LongPollService", "DatabaseService"]

