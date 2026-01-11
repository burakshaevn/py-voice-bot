"""Настройки приложения."""

import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Константы VK API
VK_API_VERSION = "5.131"
VK_API_BASE_URL = "https://api.vk.com/method"

# Настройки приложения
VK_BOT_TOKEN: Optional[str] = os.getenv("VK_BOT_TOKEN")
VK_GROUP_ID: Optional[int] = None

# Парсим VK_GROUP_ID
_group_id = os.getenv("VK_GROUP_ID")
if _group_id:
    try:
        VK_GROUP_ID = int(_group_id)
    except ValueError:
        VK_GROUP_ID = None

# Настройки Long Poll
LONG_POLL_WAIT = 25
LONG_POLL_TIMEOUT = 30

# Путь к модели голоса
DEFAULT_MODEL_PATH = None  # Используется путь по умолчанию из VoiceService

# Лимиты
MAX_TEXT_LENGTH = 1000
TEMP_AUDIO_FILE = "temp_voice.wav"

# База данных
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

# Первый админ (устанавливается при первом запуске, если БД пуста)
# Можно переопределить через переменную окружения FIRST_ADMIN_VK_ID
FIRST_ADMIN_VK_ID = os.getenv("FIRST_ADMIN_VK_ID", "199454611")

