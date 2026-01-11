"""Сервис для работы с базой данных SQLite."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import DATABASE_PATH, FIRST_ADMIN_VK_ID
from models.user import User
from models.admin import Admin

logger = logging.getLogger(__name__)


def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    Парсит строку даты из SQLite.
    
    :param date_str: Строка с датой
    :return: Объект datetime или None
    """
    if not date_str:
        return None
    
    try:
        # Пробуем ISO формат
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Пробуем простой формат
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
    except (ValueError, AttributeError):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError):
            logger.warning(f"Не удалось распарсить дату: {date_str}")
            return None


class DatabaseService:
    """Сервис для работы с базой данных."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """
        Инициализация сервиса базы данных.
        
        :param db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Получает соединение с базой данных.
        
        :return: Соединение с БД
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        return conn
    
    def _initialize_database(self) -> None:
        """Инициализирует базу данных, создавая необходимые таблицы."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vk_id INTEGER UNIQUE NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    gender INTEGER,
                    registration_date TIMESTAMP NOT NULL,
                    is_blocked BOOLEAN DEFAULT 0
                )
            """)
            
            # Таблица администраторов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vk_id INTEGER UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            
            conn.commit()
            
            # Создаем первого админа, если указан и БД пуста
            if FIRST_ADMIN_VK_ID:
                try:
                    admin_id = int(FIRST_ADMIN_VK_ID)
                    if not self.is_admin(admin_id):
                        self.add_admin(admin_id)
                        logger.info(f"Первый администратор создан: {admin_id}")
                except ValueError:
                    logger.warning(f"Неверный формат FIRST_ADMIN_VK_ID: {FIRST_ADMIN_VK_ID}")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def add_user(self, vk_id: int, first_name: str, last_name: str, 
                 gender: Optional[int] = None) -> User:
        """
        Добавляет нового пользователя в базу данных.
        
        :param vk_id: VK ID пользователя
        :param first_name: Имя
        :param last_name: Фамилия
        :param gender: Пол (1 - женский, 2 - мужской, None - не указан)
        :return: Объект пользователя
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            registration_date = datetime.now()
            
            cursor.execute("""
                INSERT OR IGNORE INTO users (vk_id, first_name, last_name, gender, registration_date, is_blocked)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (vk_id, first_name, last_name, gender, registration_date))
            
            # Если пользователь уже существует, обновляем его данные
            if cursor.rowcount == 0:
                cursor.execute("""
                    UPDATE users 
                    SET first_name = ?, last_name = ?, gender = ?
                    WHERE vk_id = ?
                """, (first_name, last_name, gender, vk_id))
            
            conn.commit()
            
            # Получаем пользователя из БД
            user = self.get_user_by_vk_id(vk_id)
            if not user:
                raise Exception(f"Не удалось создать пользователя с VK ID {vk_id}")
            
            logger.info(f"Пользователь добавлен/обновлен: {vk_id} ({first_name} {last_name})")
            return user
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_user_by_vk_id(self, vk_id: int) -> Optional[User]:
        """
        Получает пользователя по VK ID.
        
        :param vk_id: VK ID пользователя
        :return: Объект пользователя или None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users WHERE vk_id = ?
            """, (vk_id,))
            
            row = cursor.fetchone()
            if row:
                return User(
                    id=row['id'],
                    vk_id=row['vk_id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    gender=row['gender'],
                    registration_date=parse_datetime(row['registration_date']),
                    is_blocked=bool(row['is_blocked'])
                )
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
        finally:
            conn.close()
    
    def block_user(self, vk_id: int) -> bool:
        """
        Блокирует пользователя.
        
        :param vk_id: VK ID пользователя
        :return: True если успешно, False если пользователь не найден
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET is_blocked = 1 WHERE vk_id = ?
            """, (vk_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"Пользователь заблокирован: {vk_id}")
            else:
                logger.warning(f"Пользователь не найден для блокировки: {vk_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при блокировке пользователя: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def unblock_user(self, vk_id: int) -> bool:
        """
        Разблокирует пользователя.
        
        :param vk_id: VK ID пользователя
        :return: True если успешно, False если пользователь не найден
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET is_blocked = 0 WHERE vk_id = ?
            """, (vk_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"Пользователь разблокирован: {vk_id}")
            else:
                logger.warning(f"Пользователь не найден для разблокировки: {vk_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при разблокировке пользователя: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def is_user_blocked(self, vk_id: int) -> bool:
        """
        Проверяет, заблокирован ли пользователь.
        
        :param vk_id: VK ID пользователя
        :return: True если заблокирован, False если нет или не найден
        """
        user = self.get_user_by_vk_id(vk_id)
        return user.is_blocked if user else False
    
    def add_admin(self, vk_id: int) -> Admin:
        """
        Добавляет администратора.
        
        :param vk_id: VK ID администратора
        :return: Объект администратора
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            created_at = datetime.now()
            
            cursor.execute("""
                INSERT OR IGNORE INTO admins (vk_id, created_at)
                VALUES (?, ?)
            """, (vk_id, created_at))
            
            conn.commit()
            
            admin = self.get_admin_by_vk_id(vk_id)
            if not admin:
                raise Exception(f"Не удалось создать администратора с VK ID {vk_id}")
            
            logger.info(f"Администратор добавлен: {vk_id}")
            return admin
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении администратора: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_admin_by_vk_id(self, vk_id: int) -> Optional[Admin]:
        """
        Получает администратора по VK ID.
        
        :param vk_id: VK ID администратора
        :return: Объект администратора или None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM admins WHERE vk_id = ?
            """, (vk_id,))
            
            row = cursor.fetchone()
            if row:
                return Admin(
                    id=row['id'],
                    vk_id=row['vk_id'],
                    created_at=parse_datetime(row['created_at'])
                )
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении администратора: {e}")
            return None
        finally:
            conn.close()
    
    def is_admin(self, vk_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором.
        
        :param vk_id: VK ID пользователя
        :return: True если администратор, False если нет
        """
        return self.get_admin_by_vk_id(vk_id) is not None
    
    def get_all_users(self, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        """
        Получает список всех пользователей с опциональными фильтрами.
        
        :param filters: Словарь с фильтрами (gender, is_blocked, etc.)
        :return: Список пользователей
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM users WHERE 1=1"
            params = []
            
            if filters:
                if 'gender' in filters:
                    query += " AND gender = ?"
                    params.append(filters['gender'])
                
                if 'is_blocked' in filters:
                    query += " AND is_blocked = ?"
                    params.append(1 if filters['is_blocked'] else 0)
            
            query += " ORDER BY registration_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append(User(
                    id=row['id'],
                    vk_id=row['vk_id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    gender=row['gender'],
                    registration_date=parse_datetime(row['registration_date']),
                    is_blocked=bool(row['is_blocked'])
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_admins(self) -> List[Admin]:
        """
        Получает список всех администраторов.
        
        :return: Список администраторов
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM admins ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            admins = []
            for row in rows:
                admins.append(Admin(
                    id=row['id'],
                    vk_id=row['vk_id'],
                    created_at=parse_datetime(row['created_at'])
                ))
            
            return admins
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка администраторов: {e}")
            return []
        finally:
            conn.close()

