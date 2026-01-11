"""Модели данных приложения."""

from .message import Message
from .vk_update import VKUpdate
from .user import User
from .admin import Admin

__all__ = ["Message", "VKUpdate", "User", "Admin"]

