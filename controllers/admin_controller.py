"""Контроллер для административных команд."""

import logging
import re
from typing import Optional, List, Dict, Any

from models.message import Message
from services.vk_api_service import VKAPIService
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class AdminController:
    """Контроллер для обработки административных команд."""
    
    def __init__(self, vk_api: VKAPIService, db_service: DatabaseService):
        """
        Инициализация админского контроллера.
        
        :param vk_api: Сервис VK API
        :param db_service: Сервис базы данных
        """
        self.vk_api = vk_api
        self.db_service = db_service
    
    def handle_command(self, message: Message, command: str) -> bool:
        """
        Обрабатывает административную команду.
        
        :param message: Объект сообщения
        :param command: Команда с аргументами (без слэша)
        :return: True если команда обработана, False если команда не админская
        """
        # Проверяем права администратора
        if not self.db_service.is_admin(message.user_id):
            return False
        
        # Разбираем команду
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "block":
            self._handle_block(message, args)
        elif cmd == "unblock":
            self._handle_unblock(message, args)
        elif cmd == "send":
            self._handle_send(message, args)
        elif cmd == "admin":
            self._handle_admin(message, args)
        elif cmd == "stats":
            self._handle_stats(message)
        elif cmd == "broadcast":
            self._handle_broadcast(message, args)
        else:
            return False
        
        return True
    
    def _handle_block(self, message: Message, args: str) -> None:
        """
        Блокирует пользователя.
        
        Команда: /block <vk_id>
        """
        if not args:
            self.vk_api.send_message(
                message.user_id,
                "❌ Использование: /block <vk_id>\n"
                "Пример: /block 123456789"
            )
            return
        
        try:
            vk_id = int(args.strip())
            
            if vk_id == message.user_id:
                self.vk_api.send_message(
                    message.user_id,
                    "❌ Нельзя заблокировать самого себя!"
                )
                return
            
            # Проверяем, не админ ли это
            if self.db_service.is_admin(vk_id):
                self.vk_api.send_message(
                    message.user_id,
                    "❌ Нельзя заблокировать администратора!"
                )
                return
            
            success = self.db_service.block_user(vk_id)
            
            if success:
                user = self.db_service.get_user_by_vk_id(vk_id)
                user_name = user.get_full_name() if user else f"ID {vk_id}"
                self.vk_api.send_message(
                    message.user_id,
                    f"✅ Пользователь {user_name} (ID: {vk_id}) заблокирован"
                )
            else:
                self.vk_api.send_message(
                    message.user_id,
                    f"❌ Пользователь с ID {vk_id} не найден"
                )
        except ValueError:
            self.vk_api.send_message(
                message.user_id,
                "❌ Неверный формат ID. Используйте числовое значение."
            )
    
    def _handle_unblock(self, message: Message, args: str) -> None:
        """
        Разблокирует пользователя.
        
        Команда: /unblock <vk_id>
        """
        if not args:
            self.vk_api.send_message(
                message.user_id,
                "❌ Использование: /unblock <vk_id>\n"
                "Пример: /unblock 123456789"
            )
            return
        
        try:
            vk_id = int(args.strip())
            success = self.db_service.unblock_user(vk_id)
            
            if success:
                user = self.db_service.get_user_by_vk_id(vk_id)
                user_name = user.get_full_name() if user else f"ID {vk_id}"
                self.vk_api.send_message(
                    message.user_id,
                    f"✅ Пользователь {user_name} (ID: {vk_id}) разблокирован"
                )
            else:
                self.vk_api.send_message(
                    message.user_id,
                    f"❌ Пользователь с ID {vk_id} не найден"
                )
        except ValueError:
            self.vk_api.send_message(
                message.user_id,
                "❌ Неверный формат ID. Используйте числовое значение."
            )
    
    def _handle_send(self, message: Message, args: str) -> None:
        """
        Отправляет сообщение любому пользователю.
        
        Команда: /send <vk_id> <текст сообщения>
        """
        if not args:
            self.vk_api.send_message(
                message.user_id,
                "❌ Использование: /send <vk_id> <текст сообщения>\n"
                "Пример: /send 123456789 Привет!"
            )
            return
        
        # Разбираем аргументы: первый аргумент - vk_id, остальное - текст
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            self.vk_api.send_message(
                message.user_id,
                "❌ Не указан текст сообщения"
            )
            return
        
        try:
            target_vk_id = int(parts[0])
            text = parts[1]
            
            # Отправляем сообщение
            self.vk_api.send_message(target_vk_id, text)
            
            target_user = self.db_service.get_user_by_vk_id(target_vk_id)
            target_name = target_user.get_full_name() if target_user else f"ID {target_vk_id}"
            
            self.vk_api.send_message(
                message.user_id,
                f"✅ Сообщение отправлено пользователю {target_name} (ID: {target_vk_id})"
            )
        except ValueError:
            self.vk_api.send_message(
                message.user_id,
                "❌ Неверный формат ID. Используйте числовое значение."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            self.vk_api.send_message(
                message.user_id,
                f"❌ Ошибка при отправке сообщения: {str(e)}"
            )
    
    def _handle_admin(self, message: Message, args: str) -> None:
        """
        Назначает нового администратора.
        
        Команда: /admin <vk_id>
        """
        if not args:
            self.vk_api.send_message(
                message.user_id,
                "❌ Использование: /admin <vk_id>\n"
                "Пример: /admin 123456789"
            )
            return
        
        try:
            vk_id = int(args.strip())
            
            if self.db_service.is_admin(vk_id):
                self.vk_api.send_message(
                    message.user_id,
                    f"❌ Пользователь с ID {vk_id} уже является администратором"
                )
                return
            
            # Добавляем администратора
            self.db_service.add_admin(vk_id)
            
            user = self.db_service.get_user_by_vk_id(vk_id)
            user_name = user.get_full_name() if user else f"ID {vk_id}"
            
            self.vk_api.send_message(
                message.user_id,
                f"✅ Пользователь {user_name} (ID: {vk_id}) назначен администратором"
            )
            
            # Уведомляем нового админа
            self.vk_api.send_message(
                vk_id,
                "👑 Вы назначены администратором бота!\n\n"
                "Доступные команды:\n"
                "/block <vk_id> - заблокировать пользователя\n"
                "/unblock <vk_id> - разблокировать пользователя\n"
                "/send <vk_id> <текст> - отправить сообщение\n"
                "/admin <vk_id> - назначить админа\n"
                "/stats - статистика бота\n"
                "/broadcast <условия> <текст> - рассылка"
            )
        except ValueError:
            self.vk_api.send_message(
                message.user_id,
                "❌ Неверный формат ID. Используйте числовое значение."
            )
        except Exception as e:
            logger.error(f"Ошибка при назначении администратора: {e}")
            self.vk_api.send_message(
                message.user_id,
                f"❌ Ошибка: {str(e)}"
            )
    
    def _handle_stats(self, message: Message) -> None:
        """
        Показывает статистику бота.
        
        Команда: /stats
        """
        try:
            all_users = self.db_service.get_all_users()
            blocked_users = [u for u in all_users if u.is_blocked]
            all_admins = self.db_service.get_all_admins()
            
            stats_text = (
                "📊 Статистика бота:\n\n"
                f"👥 Всего пользователей: {len(all_users)}\n"
                f"🚫 Заблокированных: {len(blocked_users)}\n"
                f"✅ Активных: {len(all_users) - len(blocked_users)}\n"
                f"👑 Администраторов: {len(all_admins)}\n\n"
            )
            
            # Статистика по полу
            if all_users:
                males = sum(1 for u in all_users if u.is_male())
                females = sum(1 for u in all_users if u.is_female())
                unknown = len(all_users) - males - females
                
                stats_text += (
                    "👨 Мужчин: {}\n"
                    "👩 Женщин: {}\n"
                    "❓ Не указано: {}\n"
                ).format(males, females, unknown)
            
            self.vk_api.send_message(message.user_id, stats_text)
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            self.vk_api.send_message(
                message.user_id,
                f"❌ Ошибка при получении статистики: {str(e)}"
            )
    
    def _handle_broadcast(self, message: Message, args: str) -> None:
        """
        Выполняет рассылку сообщений по определенным правилам.
        
        Команда: /broadcast [gender=1|2] [blocked=0|1] <текст сообщения>
        Примеры:
        /broadcast gender=1 Привет, девушки!
        /broadcast gender=2 blocked=0 Привет, активные парни!
        /broadcast Привет всем!
        """
        if not args:
            self.vk_api.send_message(
                message.user_id,
                "❌ Использование: /broadcast [условия] <текст>\n\n"
                "Условия:\n"
                "gender=1 - только женщины\n"
                "gender=2 - только мужчины\n"
                "blocked=0 - только активные\n"
                "blocked=1 - только заблокированные\n\n"
                "Примеры:\n"
                "/broadcast gender=1 Привет, девушки!\n"
                "/broadcast gender=2 blocked=0 Привет, активные парни!"
            )
            return
        
        try:
            # Парсим условия и текст
            parts = args.split()
            filters: Dict[str, Any] = {}
            text_parts = []
            
            in_text = False
            for part in parts:
                if part.startswith("gender=") or part.startswith("blocked="):
                    if "=" in part:
                        key, value = part.split("=", 1)
                        if key == "gender":
                            filters["gender"] = int(value)
                        elif key == "blocked":
                            filters["is_blocked"] = bool(int(value))
                else:
                    in_text = True
                    text_parts.append(part)
            
            if not text_parts:
                self.vk_api.send_message(
                    message.user_id,
                    "❌ Не указан текст для рассылки"
                )
                return
            
            text = " ".join(text_parts)
            
            # Получаем пользователей по фильтрам
            users = self.db_service.get_all_users(filters)
            
            if not users:
                self.vk_api.send_message(
                    message.user_id,
                    "❌ Не найдено пользователей по указанным критериям"
                )
                return
            
            # Отправляем сообщения
            sent = 0
            failed = 0
            
            for user in users:
                try:
                    self.vk_api.send_message(user.vk_id, text)
                    sent += 1
                except Exception as e:
                    logger.error(f"Ошибка при отправке рассылки пользователю {user.vk_id}: {e}")
                    failed += 1
            
            # Отправляем отчет админу
            self.vk_api.send_message(
                message.user_id,
                f"✅ Рассылка завершена!\n\n"
                f"📤 Отправлено: {sent}\n"
                f"❌ Ошибок: {failed}\n"
                f"👥 Всего получателей: {len(users)}"
            )
        except Exception as e:
            logger.error(f"Ошибка при выполнении рассылки: {e}")
            self.vk_api.send_message(
                message.user_id,
                f"❌ Ошибка при выполнении рассылки: {str(e)}"
            )



