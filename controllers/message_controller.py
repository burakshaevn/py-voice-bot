"""Контроллер для обработки сообщений."""

import logging
from pathlib import Path
from typing import Optional

from config.settings import TEMP_AUDIO_FILE
from models.message import Message
from services.vk_api_service import VKAPIService
from services.voice_service import VoiceService
from services.database_service import DatabaseService
from views.message_view import MessageView

logger = logging.getLogger(__name__)


class MessageController:
    """Контроллер для обработки сообщений от пользователей."""
    
    def __init__(self, vk_api: VKAPIService, voice_service: VoiceService, 
                 db_service: DatabaseService):
        """
        Инициализация контроллера сообщений.
        
        :param vk_api: Сервис VK API
        :param voice_service: Сервис генерации голоса
        :param db_service: Сервис базы данных
        """
        self.vk_api = vk_api
        self.voice_service = voice_service
        self.db_service = db_service
        self.message_view = MessageView()
    
    def _ensure_user_exists(self, user_id: int) -> None:
        """
        Убеждается, что пользователь существует в базе данных.
        Если нет - получает информацию из VK API и создает.
        
        :param user_id: VK ID пользователя
        """
        # Проверяем, существует ли пользователь
        user = self.db_service.get_user_by_vk_id(user_id)
        if user:
            return
        
        # Получаем информацию о пользователе из VK API
        try:
            users_info = self.vk_api.get_user_info([user_id])
            if not users_info:
                logger.warning(f"Не удалось получить информацию о пользователе {user_id}")
                return
            
            user_info = users_info[0]
            first_name = user_info.get("first_name", "Неизвестно")
            last_name = user_info.get("last_name", "")
            gender = user_info.get("sex", 0)  # 1 - женский, 2 - мужской, 0 - не указан
            
            # Создаем пользователя в БД
            self.db_service.add_user(user_id, first_name, last_name, gender)
            logger.info(f"Пользователь {user_id} ({first_name} {last_name}) добавлен в БД")
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
    
    def handle_message(self, message: Message) -> None:
        """
        Обрабатывает входящее сообщение.
        
        :param message: Объект сообщения
        """
        logger.info(f"Получено сообщение от {message.user_id}: {message.text}")
        
        # Убеждаемся, что пользователь существует в БД
        try:
            self._ensure_user_exists(message.user_id)
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
        
        # Проверяем, заблокирован ли пользователь
        if self.db_service.is_user_blocked(message.user_id):
            logger.info(f"Сообщение от заблокированного пользователя {message.user_id} проигнорировано")
            return
        
        # Обработка команд
        if message.is_command():
            self._handle_command(message)
            return
        
        # Проверка на пустой текст
        if not message.text or not message.text.strip():
            self.vk_api.send_message(
                message.user_id,
                self.message_view.format_empty_text_message()
            )
            return
        
        # Генерация голосового сообщения
        try:
            # Генерируем голосовое сообщение
            audio_data = self.voice_service.generate_voice_message(message.text)
            
            # Сохраняем во временный файл
            temp_file = self.voice_service.save_audio_to_temp_file(audio_data, TEMP_AUDIO_FILE)
            
            try:
                # Загружаем и отправляем голосовое сообщение
                attachment = self.vk_api.upload_audio_message(str(temp_file), message.peer_id)
                self.vk_api.send_message(
                    message.user_id,
                    "",  # Пустое текстовое сообщение, только голосовое
                    attachment=attachment
                )
                logger.info(f"Голосовое сообщение отправлено пользователю {message.user_id}")
            finally:
                # Удаляем временный файл
                temp_file.unlink(missing_ok=True)
        
        except Exception as e:
            logger.error(f"Ошибка при генерации голосового сообщения: {e}", exc_info=True)
            self.vk_api.send_message(
                message.user_id,
                self.message_view.format_error_message(str(e))
            )
    
    def _handle_command(self, message: Message) -> None:
        """
        Обрабатывает команды от пользователя.
        
        :param message: Объект сообщения с командой
        """
        command = message.get_command()
        
        if command == "start":
            self.vk_api.send_message(
                message.user_id,
                self.message_view.format_welcome_message()
            )
        elif command == "help":
            self.vk_api.send_message(
                message.user_id,
                self.message_view.format_help_message()
            )
        else:
            # Неизвестная команда
            logger.warning(f"Неизвестная команда от {message.user_id}: {command}")
            self.vk_api.send_message(
                message.user_id,
                f"❓ Неизвестная команда: /{command}\nИспользуйте /help для справки."
            )

