"""Главный файл приложения для запуска бота."""

import logging
import os
import time
from dotenv import load_dotenv

from config.settings import VK_BOT_TOKEN, VK_GROUP_ID
from services.vk_api_service import VKAPIService
from services.voice_service import VoiceService
from services.long_poll_service import LongPollService
from services.database_service import DatabaseService
from controllers.message_controller import MessageController
from controllers.admin_controller import AdminController
from models.message import Message
from models.vk_update import VKUpdate

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VKBotApp:
    """Главный класс приложения бота."""
    
    def __init__(self):
        """Инициализация приложения."""
        # Проверка токена
        if not VK_BOT_TOKEN:
            raise ValueError("VK_BOT_TOKEN не установлен! Установите токен в переменных окружения.")
        
        # Инициализация сервисов
        logger.info("Инициализация сервисов...")
        self.db_service = DatabaseService()
        self.vk_api = VKAPIService(VK_BOT_TOKEN)
        self.voice_service = VoiceService()
        self.long_poll = LongPollService(self.vk_api, VK_GROUP_ID)
        
        # Инициализация контроллеров
        self.message_controller = MessageController(
            self.vk_api, 
            self.voice_service, 
            self.db_service
        )
        self.admin_controller = AdminController(self.vk_api, self.db_service)
        
        logger.info("Приложение успешно инициализировано")
    
    def run(self) -> None:
        """Запускает основной цикл бота."""
        logger.info("Запуск голосового бота ВКонтакте...")
        
        while True:
            try:
                # Получаем обновления
                updates = self.long_poll.get_updates()
                
                # Обрабатываем каждое обновление
                for update in updates:
                    self._process_update(update)
            
            except KeyboardInterrupt:
                logger.info("Остановка бота...")
                break
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)
                time.sleep(5)
    
    def _process_update(self, update: VKUpdate) -> None:
        """
        Обрабатывает одно обновление от Long Poll.
        
        :param update: Объект обновления
        """
        # Пропускаем обновления, которые не являются сообщениями
        if not update.is_message():
            return
        
        # Извлекаем данные сообщения
        message_data = update.extract_message()
        if not message_data:
            return
        
        # Создаем объект сообщения
        message = Message(
            user_id=message_data["user_id"],
            text=message_data["text"],
            message_id=message_data.get("message_id")
        )
        
        # Проверяем, является ли команда админской
        if message.is_command():
            # Передаем всю команду без слэша (включая аргументы)
            command_with_args = message.text[1:] if message.text.startswith("/") else message.text
            if command_with_args and self.admin_controller.handle_command(message, command_with_args):
                # Команда обработана админским контроллером
                return
        
        # Передаем в обычный контроллер для обработки
        self.message_controller.handle_message(message)


def main():
    """Главная функция для запуска приложения."""
    try:
        app = VKBotApp()
        app.run()
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске приложения: {e}", exc_info=True)


if __name__ == "__main__":
    main()

