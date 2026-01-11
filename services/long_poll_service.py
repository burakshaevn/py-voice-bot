"""Сервис для работы с VK Long Poll."""

import logging
import requests
from typing import Optional, List, Any

from config.settings import LONG_POLL_WAIT, LONG_POLL_TIMEOUT
from services.vk_api_service import VKAPIService
from models.vk_update import VKUpdate

logger = logging.getLogger(__name__)


class LongPollService:
    """Сервис для работы с VK Long Poll."""
    
    def __init__(self, vk_api: VKAPIService, group_id: Optional[int] = None):
        """
        Инициализация сервиса Long Poll.
        
        :param vk_api: Сервис VK API
        :param group_id: ID группы (опционально)
        """
        self.vk_api = vk_api
        self.group_id = group_id
        self.ts: Optional[str] = None
        self.server: Optional[str] = None
        self.key: Optional[str] = None
        self._initialize()
    
    def _initialize(self) -> None:
        """Инициализирует соединение с Long Poll сервером."""
        try:
            result = self.vk_api.get_long_poll_server(self.group_id)
            self.server = result["server"]
            self.key = result["key"]
            self.ts = result["ts"]
        except Exception as e:
            logger.error(f"Ошибка при инициализации Long Poll: {e}")
            raise
    
    def get_updates(self) -> List[VKUpdate]:
        """
        Получает обновления через Long Poll.
        
        :return: Список обновлений
        """
        if not self.server or not self.key or self.ts is None:
            self._initialize()
        
        url = f"https://{self.server}"
        params = {
            "act": "a_check",
            "key": self.key,
            "ts": self.ts,
            "wait": LONG_POLL_WAIT
        }
        
        try:
            response = requests.get(url, params=params, timeout=LONG_POLL_TIMEOUT)
            data = response.json()
            
            if "failed" in data:
                if data["failed"] == 1:
                    # Обновить ts
                    self.ts = data["ts"]
                    return []
                elif data["failed"] in [2, 3]:
                    # Переподключиться
                    self._initialize()
                    return []
            
            self.ts = data["ts"]
            updates_data = data.get("updates", [])
            
            # Преобразуем в модели VKUpdate
            updates = []
            for update_data in updates_data:
                if isinstance(update_data, list) and len(update_data) > 0:
                    update_type = update_data[0]
                    updates.append(VKUpdate(update_type=update_type, update_data=update_data))
            
            return updates
        
        except requests.exceptions.Timeout:
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении обновлений: {e}")
            return []



