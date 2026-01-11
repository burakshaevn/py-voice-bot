"""Модель сообщения."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """Модель сообщения от пользователя."""
    
    user_id: int
    text: str
    message_id: Optional[int] = None
    peer_id: Optional[int] = None
    
    def __post_init__(self):
        """Устанавливает peer_id равным user_id, если не указан."""
        if self.peer_id is None:
            self.peer_id = self.user_id
    
    def is_command(self) -> bool:
        """Проверяет, является ли сообщение командой."""
        return self.text and self.text.startswith("/")
    
    def get_command(self) -> Optional[str]:
        """Возвращает команду без слэша."""
        if self.is_command():
            parts = self.text.split(maxsplit=1)
            return parts[0][1:] if len(parts) > 0 else None
        return None



