"""Сервис для генерации голосовых сообщений."""

import logging
import re
from pathlib import Path
from typing import Optional

from voice_generator import VoiceGenerator

logger = logging.getLogger(__name__)


class VoiceService:
    """Сервис для генерации голосовых сообщений."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация сервиса генерации голоса.
        
        :param model_path: Путь к модели .onnx. Если None, используется модель по умолчанию.
        """
        try:
            self.voice_generator = VoiceGenerator(model_path)
            logger.info("Сервис генерации голоса успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации генератора голоса: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """
        Очищает текст от HTML-тегов и лишних пробелов.
        
        :param text: Исходный текст
        :return: Очищенный текст
        """
        # Заменяем <br> на пробелы, удаляем остальные теги
        text_cleaned = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
        text_cleaned = re.sub(r'<[^>]+>', '', text_cleaned)
        # Убираем лишние пробелы
        text_cleaned = ' '.join(text_cleaned.split())
        return text_cleaned
    
    def generate_voice_message(self, text: str, output_path: Optional[str] = None) -> bytes:
        """
        Генерирует голосовое сообщение из текста.
        
        :param text: Текст для озвучки
        :param output_path: Путь для сохранения файла (опционально)
        :return: Байты аудиофайла
        """
        # Очищаем текст
        text_cleaned = self.clean_text(text)
        
        if not text_cleaned:
            raise ValueError("Текст пуст после очистки")
        
        # Генерируем голосовое сообщение
        audio_data = self.voice_generator.text_to_ogg(text_cleaned)
        
        # Сохраняем во временный файл, если указан путь
        if output_path:
            output_file = Path(output_path)
            output_file.write_bytes(audio_data)
            logger.info(f"Голосовое сообщение сохранено в {output_path}")
        
        return audio_data
    
    def save_audio_to_temp_file(self, audio_data: bytes, temp_path: str = "temp_voice.wav") -> Path:
        """
        Сохраняет аудиоданные во временный файл.
        
        :param audio_data: Байты аудиофайла
        :param temp_path: Путь к временному файлу
        :return: Путь к созданному файлу
        """
        temp_file = Path(temp_path)
        temp_file.write_bytes(audio_data)
        return temp_file



