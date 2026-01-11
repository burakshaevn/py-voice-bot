"""Модель администратора."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Admin:
    """Модель администратора в базе данных."""
    
    vk_id: int
    created_at: Optional[datetime] = None
    id: Optional[int] = None  # ID в базе данных
    
    def __post_init__(self):
        """Устанавливает дату создания, если не указана."""
        if self.created_at is None:
            self.created_at = datetime.now()



