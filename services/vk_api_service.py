"""Сервис для работы с VK API."""

import logging
import requests
import time
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import VK_API_VERSION, VK_API_BASE_URL

logger = logging.getLogger(__name__)


class VKAPIService:
    """Сервис для работы с VK API."""
    
    def __init__(self, token: str):
        """
        Инициализация сервиса VK API.
        
        :param token: Токен доступа VK API
        """
        self.token = token
    
    def _api_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполняет запрос к VK API.
        
        :param method: Название метода API
        :param params: Параметры запроса
        :return: Ответ API
        """
        if params is None:
            params = {}
        
        params["access_token"] = self.token
        params["v"] = VK_API_VERSION
        
        response = requests.post(
            f"{VK_API_BASE_URL}/{method}",
            data=params
        )
        
        result = response.json()
        
        if "error" in result:
            logger.error(f"VK API Error: {result['error']}")
            raise Exception(f"VK API Error: {result['error']}")
        
        return result.get("response", {})
    
    def send_message(self, user_id: int, message: str, attachment: Optional[str] = None) -> None:
        """
        Отправляет сообщение пользователю.
        
        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param attachment: Вложение (например, документ)
        """
        params = {
            "user_id": user_id,
            "message": message,
            "random_id": int(time.time() * 1000)
        }
        
        if attachment:
            params["attachment"] = attachment
        
        self._api_request("messages.send", params)
        logger.info(f"Сообщение отправлено пользователю {user_id}")
    
    def upload_audio_message(self, file_path: str, peer_id: int) -> str:
        """
        Загружает голосовое сообщение в VK.
        
        :param file_path: Путь к аудиофайлу
        :param peer_id: ID получателя
        :return: Строка вложения для отправки сообщения
        """
        # 1. Получаем сервер для загрузки
        upload_server = self._api_request("docs.getMessagesUploadServer", {
            "type": "audio_message",
            "peer_id": peer_id
        })
        
        upload_url = upload_server["upload_url"]
        
        # 2. Загружаем файл
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(upload_url, files=files)
            upload_result = response.json()
        
        # 3. Сохраняем документ
        doc = self._api_request("docs.save", {
            "file": upload_result["file"]
        })
        
        audio_doc = doc["audio_message"]
        owner_id = audio_doc["owner_id"]
        doc_id = audio_doc["id"]
        
        # Возвращаем строку вложения
        return f"doc{owner_id}_{doc_id}"
    
    def get_long_poll_server(self, group_id: Optional[int] = None) -> Dict[str, str]:
        """
        Получает сервер для Long Poll.
        
        :param group_id: ID группы (опционально)
        :return: Словарь с server, key и ts
        """
        if group_id:
            result = self._api_request("groups.getLongPollServer", {
                "group_id": group_id
            })
        else:
            # Для пользовательского токена используем другой метод
            result = self._api_request("messages.getLongPollServer")
        
        logger.info(f"Long Poll сервер получен: {result['server']}")
        return result
    
    def get_user_info(self, user_ids: list[int]) -> list[Dict[str, Any]]:
        """
        Получает информацию о пользователях.
        
        :param user_ids: Список ID пользователей
        :return: Список словарей с информацией о пользователях
        """
        if not user_ids:
            return []
        
        try:
            result = self._api_request("users.get", {
                "user_ids": ",".join(map(str, user_ids)),
                "fields": "sex"  # Получаем также пол пользователя
            })
            
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователях: {e}")
            return []
    
    def get_unread_conversations(self, count: int = 20) -> list[Dict[str, Any]]:
        """
        Получает список непрочитанных диалогов.
        
        :param count: Количество диалогов для получения
        :return: Список диалогов с информацией о последнем сообщении
        """
        try:
            result = self._api_request("messages.getConversations", {
                "filter": "unread",  # Только непрочитанные
                "count": count,
                "extended": 0
            })
            
            items = result.get("items", [])
            conversations = []
            
            for item in items:
                conversation = item.get("conversation", {})
                last_message = item.get("last_message", {})
                
                # Получаем peer_id (ID собеседника)
                peer_id = conversation.get("peer", {}).get("id")
                if not peer_id:
                    continue
                
                # Извлекаем текст последнего сообщения
                text = last_message.get("text", "").strip()
                
                # Пропускаем пустые сообщения
                if not text:
                    continue
                
                conversations.append({
                    "peer_id": peer_id,
                    "text": text,
                    "date": last_message.get("date", 0)
                })
            
            # Сортируем по дате (новые первыми)
            conversations.sort(key=lambda x: x["date"], reverse=True)
            
            return conversations[:count]
        except Exception as e:
            logger.error(f"Ошибка при получении непрочитанных диалогов: {e}")
            return []

