"""Модель пользователя."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Модель пользователя в базе данных."""
    
    vk_id: int
    first_name: str
    last_name: str
    gender: Optional[int] = None  # 1 - женский, 2 - мужской, 0 - не указан
    registration_date: Optional[datetime] = None
    is_blocked: bool = False
    id: Optional[int] = None  # ID в базе данных
    
    def __post_init__(self):
        """Устанавливает дату регистрации, если не указана."""
        if self.registration_date is None:
            self.registration_date = datetime.now()
    
    def is_female(self) -> bool:
        """Проверяет, является ли пользователь женщиной."""
        return self.gender == 1
    
    def is_male(self) -> bool:
        """Проверяет, является ли пользователь мужчиной."""
        return self.gender == 2
    
    def get_full_name(self) -> str:
        """Возвращает полное имя пользователя."""
        return f"{self.first_name} {self.last_name}"



