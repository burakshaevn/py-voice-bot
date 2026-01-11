"""Модель обновления от VK Long Poll."""

from dataclasses import dataclass
from typing import Any, Optional, List


@dataclass
class VKUpdate:
    """Модель обновления от VK Long Poll."""
    
    update_type: int
    update_data: List[Any]
    
    def is_message(self) -> bool:
        """Проверяет, является ли обновление новым сообщением."""
        return self.update_type == 4
    
    def is_outgoing(self) -> bool:
        """Проверяет, является ли сообщение исходящим."""
        if not self.is_message() or len(self.update_data) < 3:
            return False
        
        flags = self.update_data[2]
        # Флаг 2 = исходящее сообщение
        return bool(flags & 2)
    
    def extract_message(self) -> Optional[dict]:
        """
        Извлекает данные сообщения из обновления.
        
        :return: Словарь с user_id и text, или None если не удалось извлечь
        """
        if not self.is_message() or len(self.update_data) < 4:
            return None
        
        if self.is_outgoing():
            return None
        
        user_id = None
        text = ""
        message_id = None
        
        # Определяем user_id
        if isinstance(self.update_data[3], int):
            user_id = self.update_data[3]
            message_id = self.update_data[1] if len(self.update_data) > 1 else None
        elif isinstance(self.update_data[3], dict):
            # Формат токена группы
            message_data = self.update_data[3]
            user_id = message_data.get("from_id") or message_data.get("user_id")
            text = message_data.get("text", "").strip()
            message_id = message_data.get("id")
        
        # Если user_id не найден, возвращаем None
        if not user_id:
            return None
        
        # Если текст уже извлечен из словаря, используем его
        if not text:
            # Ищем текст в последних элементах списка (пропускаем служебные строки)
            for item in reversed(self.update_data):
                if isinstance(item, str):
                    item_stripped = item.strip()
                    # Пропускаем пустые строки и служебные значения
                    if item_stripped and item_stripped not in ['...', ' ... ', '']:
                        text = item_stripped
                        break
        
        return {
            "user_id": user_id,
            "text": text,
            "message_id": message_id
        }

